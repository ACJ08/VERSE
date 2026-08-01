"""
VERSE Services - Script Intelligence → Continuity Engine Ingest Bridge.

Converts structured SceneContinuity output (from ContinuityService / GraniteClient)
into the JSON payload shape expected by the continuity-engine's
POST /continuity/ingest/script endpoint, then forwards it.

The bridge is intentionally stateless — it makes a single HTTP POST per call
and returns the raw engine response.  The caller (the /analyse-and-ingest endpoint
or any service) is responsible for deciding whether to forward on a per-request basis.

Configuration (via environment variables or Settings):
    CONTINUITY_ENGINE_URL   Base URL of the continuity-engine FastAPI service
                            (default: http://localhost:8000)
    CONTINUITY_ENGINE_TOKEN (optional) Bearer token for the engine.
                            Required only when the engine is running behind auth.
"""

from __future__ import annotations

import os
import logging
from typing import List, Optional

import httpx

from app.schemas.continuity import SceneContinuity

logger = logging.getLogger(__name__)

# Allow override via env — defaults to the continuity-engine dev address.
_ENGINE_BASE_URL = os.getenv("CONTINUITY_ENGINE_URL", "http://localhost:8000").rstrip("/")
_ENGINE_TOKEN = os.getenv("CONTINUITY_ENGINE_TOKEN", "")
_HTTP_TIMEOUT = float(os.getenv("CONTINUITY_ENGINE_TIMEOUT", "30"))


def _scene_continuity_to_engine_payload(
    scenes: List[SceneContinuity],
    project_id: str = "",
) -> dict:
    """Convert a list of SceneContinuity objects to the continuity-engine scene JSON.

    Returns a dict with ``project_id``, ``source``, and ``scenes`` — everything
    the engine's ingest endpoint needs.  The caller passes this dict as both the
    top-level ``project_id`` field *and* the inner ``payload`` when building the
    final POST body.

    Engine IngestRequest shape:
      POST /continuity/ingest/script
      {"project_id": "<id>", "payload": {"source": "script", "scenes": [...]}}
    """
    engine_scenes = []
    for idx, sc in enumerate(scenes):
        meta = sc.metadata
        scene_entry: dict = {
            "scene_id": meta.scene_id,
            "sequence": idx + 1,
            "location": meta.heading or meta.location or "",
            "time_of_day": meta.time or "DAY",
            "characters": [
                {
                    "name": ch.name,
                    "type": "character",
                    "costume": ch.costume,
                    "position": ch.position,
                    "movement": ch.movement,
                    "emotional_state": ch.emotional_state,
                }
                for ch in sc.characters
            ],
            "props": [
                {
                    "name": prop.name,
                    "type": "prop",
                    "hand_usage": prop.hand_usage,
                    "state": prop.state,
                    "owner": prop.owner,
                }
                for prop in sc.props
            ],
        }
        if sc.lighting:
            scene_entry["lighting"] = {
                "description": sc.lighting.description,
                "source": sc.lighting.source,
                "mood": sc.lighting.mood,
                "time_of_day": sc.lighting.time_of_day,
            }
        engine_scenes.append(scene_entry)

    return {
        "project_id": project_id,
        "source": "script",
        "scenes": engine_scenes,
    }


def forward_scenes_to_engine(
    scenes: List[SceneContinuity],
    project_id: str,
) -> Optional[dict]:
    """POST structured scene data to the continuity engine.

    Returns the engine response dict on success, or None on failure.
    Failures are logged as warnings — they must never break the calling request.
    """
    if not scenes:
        return None

    payload_body = _scene_continuity_to_engine_payload(scenes, project_id)

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if _ENGINE_TOKEN:
        headers["Authorization"] = f"Bearer {_ENGINE_TOKEN}"

    ingest_url = f"{_ENGINE_BASE_URL}/continuity/ingest/script"
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            resp = client.post(
                ingest_url,
                json={"project_id": project_id, "payload": payload_body},
                headers=headers,
            )
            resp.raise_for_status()
            logger.info(
                "Forwarded %d scenes for project '%s' to continuity engine → %s facts ingested",
                len(scenes),
                project_id,
                resp.json().get("facts_ingested", "?"),
            )
            return resp.json()
    except Exception as exc:
        logger.warning(
            "Failed to forward scenes to continuity engine at %s: %s",
            ingest_url,
            exc,
        )
        return None
