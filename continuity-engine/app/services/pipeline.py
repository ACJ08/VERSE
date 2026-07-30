"""Ingestion pipeline — upstream services in, continuity report out.

This is the seam between the three teams. The script service (team 1) and the
vision service (team 2) each own a document → structured JSON step; this module
calls them, runs the result through `app/adapters/`, ingests it, and hands back
a `ContinuityReport`.

Both upstream calls are optional. `SCRIPT_SERVICE_URL` / `VISION_SERVICE_URL`
point at the services when they are running; when they are not set — or the
service is down — the caller falls back to the local extraction path in
`app/api/upload.py`. A screenplay upload never fails because a sibling service
is offline.

    SCRIPT_SERVICE_URL=http://localhost:8100
    VISION_SERVICE_URL=http://localhost:8200
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from app.adapters import adapt_any, adapt_vision, detect_shape
from app.engine import ContinuityEngine
from app.models.schemas import ContinuityReport, SourceType

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "120"))


# --------------------------------------------------------------------------- #
# Result of one ingestion run
# --------------------------------------------------------------------------- #


@dataclass
class IngestionResult:
    """What one pipeline run ingested, and what the engine made of it."""

    project_id: str
    source: SourceType
    extractor: str
    facts_ingested: int = 0
    scene_ids: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    notes: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    frames_analysed: int = 0
    duplicate: bool = False
    stats: dict[str, int] = field(default_factory=dict)
    report: ContinuityReport | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "project_id": self.project_id,
            "source": self.source.value,
            "extractor": self.extractor,
            "facts_ingested": self.facts_ingested,
            "scenes_detected": len(self.scene_ids),
            "scene_ids": self.scene_ids,
            "entities": self.entities,
            "notes": self.notes,
            "warnings": self.warnings,
            "frames_analysed": self.frames_analysed,
            "duplicate": self.duplicate,
            "graph_stats": self.stats,
        }
        if self.report is not None:
            payload["report"] = self.report.model_dump(mode="json")
        return payload


# --------------------------------------------------------------------------- #
# Ingestion
# --------------------------------------------------------------------------- #


def ingest_payload(
    engine: ContinuityEngine,
    project_id: str,
    payload: Any,
    *,
    source: SourceType | None = None,
    extractor: str | None = None,
    analyse: bool = False,
    scene_id: str | None = None,
    entity_aliases: dict[str, Any] | None = None,
) -> IngestionResult:
    """Adapt a payload of any recognised shape, ingest it, optionally analyse.

    `source` overrides the source the detected shape implies — needed when a
    payload is already in the engine's own shape and only the caller knows
    whether it describes intent (script) or footage.
    """
    adapted = adapt_any(
        payload,
        default_source=source or SourceType.SCRIPT,
        scene_id=scene_id,
        entity_aliases=_merge_aliases(engine, entity_aliases),
    )
    resolved_source = source or adapted.source
    resolved_extractor = extractor or _default_extractor(resolved_source)

    facts = engine.ingest(adapted.payload, resolved_source, resolved_extractor)
    result = IngestionResult(
        project_id=project_id,
        source=resolved_source,
        extractor=resolved_extractor,
        facts_ingested=len(facts),
        scene_ids=adapted.scene_ids,
        entities=adapted.entities,
        notes=adapted.notes,
        warnings=list(adapted.warnings),
        frames_analysed=adapted.frames_analysed,
        stats=engine.stats(),
    )
    if analyse:
        result.report = engine.analyse()
    return result


def ingest_vision_document(
    engine: ContinuityEngine,
    project_id: str,
    payload: Any,
    *,
    scene_id: str | None = None,
    entity_aliases: dict[str, Any] | None = None,
    analyse: bool = False,
) -> IngestionResult:
    """Ingest a vision scene document, aggregating its frames first."""
    adapted = adapt_vision(
        payload,
        scene_id=scene_id,
        entity_aliases=_merge_aliases(engine, entity_aliases),
    )
    facts = engine.ingest_footage(adapted.payload, "vision")
    result = IngestionResult(
        project_id=project_id,
        source=SourceType.FOOTAGE,
        extractor="vision",
        facts_ingested=len(facts),
        scene_ids=adapted.scene_ids,
        entities=adapted.entities,
        warnings=list(adapted.warnings),
        frames_analysed=adapted.frames_analysed,
        stats=engine.stats(),
    )
    if analyse:
        result.report = engine.analyse()
    return result


def _default_extractor(source: SourceType) -> str:
    return {
        SourceType.SCRIPT: "granite",
        SourceType.FOOTAGE: "vision",
        SourceType.CALL_SHEET: "call-sheet-parser",
    }.get(source, "unknown")


def _merge_aliases(
    engine: ContinuityEngine, overrides: dict[str, Any] | None
) -> dict[str, Any]:
    """Per-request aliases win over the project's configured table."""
    merged: dict[str, Any] = dict(engine.config.entity_aliases)
    if overrides:
        merged.update(overrides)
    return merged


# --------------------------------------------------------------------------- #
# Upstream service clients
# --------------------------------------------------------------------------- #


class UpstreamUnavailable(RuntimeError):
    """The upstream service is not configured, not reachable, or errored."""


class _ServiceClient:
    """Minimal multipart-upload client shared by both upstream services."""

    env_var = ""
    name = ""

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        self.base_url = (base_url or os.getenv(self.env_var, "")).rstrip("/")
        self.timeout = timeout or _DEFAULT_TIMEOUT

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    def _post_file(
        self,
        path: str,
        filename: str,
        data: bytes,
        *,
        fields: dict[str, str] | None = None,
        field_name: str = "file",
    ) -> dict[str, Any]:
        if not self.is_configured:
            raise UpstreamUnavailable(f"{self.name} is not configured ({self.env_var} unset).")
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - httpx ships in requirements
            raise UpstreamUnavailable("httpx is not installed.") from exc

        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    files={field_name: (filename, data)},
                    data=fields or {},
                )
                response.raise_for_status()
                body = response.json()
        except Exception as exc:  # noqa: BLE001 - any failure means "fall back"
            logger.warning("%s call to %s failed: %s", self.name, url, exc)
            raise UpstreamUnavailable(f"{self.name} at {url} is unavailable: {exc}") from exc

        if not isinstance(body, dict):
            raise UpstreamUnavailable(f"{self.name} returned {type(body).__name__}, expected an object.")
        return body


class ScriptServiceClient(_ServiceClient):
    """Team 1's screenplay + call-sheet intelligence service."""

    env_var = "SCRIPT_SERVICE_URL"
    name = "Script Intelligence service"

    def analyse_script(self, filename: str, data: bytes) -> dict[str, Any]:
        """POST the screenplay to `/api/v1/analyse-script` for Granite extraction."""
        body = self._post_file("/api/v1/analyse-script", filename, data)
        if detect_shape(body) != "script_intelligence":
            raise UpstreamUnavailable(
                "Script service response did not contain any scenes with metadata."
            )
        return body

    def parse_call_sheet(self, filename: str, data: bytes) -> dict[str, Any]:
        return self._post_file("/api/v1/parse-call-sheet", filename, data)


class VisionServiceClient(_ServiceClient):
    """Team 2's footage-processing service."""

    env_var = "VISION_SERVICE_URL"
    name = "Vision service"

    def process_clip(self, filename: str, data: bytes, scene_id: str) -> dict[str, Any]:
        """POST the clip to `/process` and get back a vision scene document."""
        return self._post_file(
            "/process", filename, data, fields={"scene_id": scene_id}, field_name="video"
        )


def script_service() -> ScriptServiceClient:
    return ScriptServiceClient()


def vision_service() -> VisionServiceClient:
    return VisionServiceClient()


__all__ = [
    "IngestionResult",
    "ScriptServiceClient",
    "UpstreamUnavailable",
    "VisionServiceClient",
    "ingest_payload",
    "ingest_vision_document",
    "script_service",
    "vision_service",
]
