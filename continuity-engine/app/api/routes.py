"""FastAPI router for the continuity engine.

Team 5 mounts this into the shared backend:

    from app.api.routes import router
    app.include_router(router)

The router owns no business logic — it is a thin HTTP shell over
`ContinuityEngine` so the engine stays usable as a plain library.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.schemas import (
    ContinuityReport,
    FactOverride,
    FeedbackAction,
    Issue,
    SourceType,
)
# Unified engine registry and deduplication helpers — shared with projects
# router so every project_id maps to exactly one ContinuityEngine instance.
from app.api.projects import (
    get_or_create_engine as get_engine,
    is_duplicate_payload,
    payload_hash,
    record_payload_hash,
)

router = APIRouter(prefix="/continuity", tags=["continuity"])


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #


class IngestRequest(BaseModel):
    project_id: str = "VERSE_DEMO"
    payload: Any = Field(..., description="Arbitrary nested JSON from the producing team")
    extractor: str | None = None


class AnalyseRequest(BaseModel):
    project_id: str = "VERSE_DEMO"
    scene_id: str | None = None


class FeedbackRequest(BaseModel):
    project_id: str = "VERSE_DEMO"
    action: FeedbackAction


class OverrideRequest(BaseModel):
    project_id: str = "VERSE_DEMO"
    override: FactOverride


class IngestResponse(BaseModel):
    project_id: str
    facts_ingested: int
    stats: dict[str, int]


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #


@router.post("/ingest/script", response_model=IngestResponse)
def ingest_script(request: IngestRequest) -> IngestResponse:
    """Accept structured script JSON (team 1). Duplicate payloads are skipped."""
    h = payload_hash(request.payload)
    if is_duplicate_payload(request.project_id, h):
        engine = get_engine(request.project_id)
        return IngestResponse(
            project_id=request.project_id, facts_ingested=0, stats=engine.stats()
        )
    engine = get_engine(request.project_id)
    facts = engine.ingest_script(request.payload, request.extractor or "granite")
    record_payload_hash(request.project_id, h)
    return IngestResponse(
        project_id=request.project_id, facts_ingested=len(facts), stats=engine.stats()
    )


@router.post("/ingest/footage", response_model=IngestResponse)
def ingest_footage(request: IngestRequest) -> IngestResponse:
    """Accept structured footage observations (team 2). Duplicate payloads are skipped."""
    h = payload_hash(request.payload)
    if is_duplicate_payload(request.project_id, h):
        engine = get_engine(request.project_id)
        return IngestResponse(
            project_id=request.project_id, facts_ingested=0, stats=engine.stats()
        )
    engine = get_engine(request.project_id)
    facts = engine.ingest_footage(request.payload, request.extractor or "vision")
    record_payload_hash(request.project_id, h)
    return IngestResponse(
        project_id=request.project_id, facts_ingested=len(facts), stats=engine.stats()
    )


@router.post("/ingest/{source}", response_model=IngestResponse)
def ingest_source(source: str, request: IngestRequest) -> IngestResponse:
    """Accept any payload with an explicit source type (call sheets, notes). Duplicate payloads skipped."""
    try:
        source_type = SourceType(source)
    except ValueError as exc:
        valid = ", ".join(s.value for s in SourceType)
        raise HTTPException(422, f"Unknown source '{source}'. Expected one of: {valid}") from exc
    h = payload_hash(request.payload)
    if is_duplicate_payload(request.project_id, h):
        engine = get_engine(request.project_id)
        return IngestResponse(
            project_id=request.project_id, facts_ingested=0, stats=engine.stats()
        )
    engine = get_engine(request.project_id)
    facts = engine.ingest(request.payload, source_type, request.extractor)
    record_payload_hash(request.project_id, h)
    return IngestResponse(
        project_id=request.project_id, facts_ingested=len(facts), stats=engine.stats()
    )


@router.post("/analyse", response_model=ContinuityReport)
def analyse(request: AnalyseRequest) -> ContinuityReport:
    """Run continuity analysis and return the full report."""
    engine = get_engine(request.project_id)
    return engine.analyse(request.scene_id)


@router.get("/issues/{project_id}", response_model=list[Issue])
def list_issues(project_id: str) -> list[Issue]:
    """Current issues without re-running analysis."""
    return get_engine(project_id).issues()


@router.post("/feedback", response_model=Issue)
def submit_feedback(request: FeedbackRequest) -> Issue:
    """Record a human decision (confirm / dismiss / resolve / reopen)."""
    engine = get_engine(request.project_id)
    issue = engine.apply_feedback(request.action)
    if issue is None:
        raise HTTPException(404, f"Unknown issue '{request.action.issue_id}'")
    return issue


@router.post("/facts/override")
def override_fact(request: OverrideRequest) -> dict[str, Any]:
    """Record a human fact correction. Outranks all AI-produced facts."""
    engine = get_engine(request.project_id)
    fact = engine.override_fact(request.override)
    return {"fact_id": fact.fact_id, "value": fact.value, "human_confirmed": True}


@router.get("/health")
def health() -> dict[str, Any]:
    from app.api.projects import _ENGINES
    return {"status": "ok", "projects": list(_ENGINES)}
