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

# Unified engine registry and deduplication helpers — shared with projects
# router so every project_id maps to exactly one ContinuityEngine instance.
from app.api.projects import (
    get_or_create_engine as get_engine,
    is_duplicate_payload,
    payload_hash,
    record_payload_hash,
)
from app.models.schemas import (
    ContinuityReport,
    EntityView,
    FactOverride,
    FeedbackAction,
    Issue,
    SceneView,
    SourceType,
)
from app.reporting.views import entity_views, project_overview, scene_views
from app.services.pipeline import ingest_payload, ingest_vision_document

router = APIRouter(prefix="/continuity", tags=["continuity"])

# Shape name -> the source type that shape implies.
_SHAPE_SOURCES: dict[str, SourceType] = {
    "script": SourceType.SCRIPT,
    "footage": SourceType.FOOTAGE,
    "call_sheet": SourceType.CALL_SHEET,
}


def _csv(value: str | None) -> set[str] | None:
    """Parse a comma-separated query filter into a set, or None for "no filter"."""
    if not value:
        return None
    parts = {part.strip() for part in value.split(",") if part.strip()}
    return parts or None


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


class PipelineIngestRequest(BaseModel):
    """Ingest a payload in a producing team's own shape.

    The payload is run through `app/adapters/` first, so team 1 can post an
    `AnalyseScriptResponse` and team 2 a vision scene document without either
    of them reshaping to the engine's contract.
    """

    project_id: str = "VERSE_DEMO"
    payload: Any = Field(..., description="Team 1 / team 2 payload, in their own shape")
    scene_id: str | None = Field(
        None, description="Scene id for vision documents that do not carry one"
    )
    entity_aliases: dict[str, Any] | None = Field(
        None,
        description='Join vision track ids to script names, e.g. {"PERSON_1": "Sarah"}',
    )
    source: SourceType | None = Field(
        None, description="Override the source implied by the payload shape"
    )
    extractor: str | None = None
    analyse: bool = Field(False, description="Run analysis and include the report in the response")


class PipelineRunRequest(BaseModel):
    """Ingest a script payload and a footage payload together, then analyse."""

    project_id: str = "VERSE_DEMO"
    script: Any | None = None
    footage: Any | None = None
    call_sheet: Any | None = None
    scene_id: str | None = None
    entity_aliases: dict[str, Any] | None = None


class ProjectViewResponse(BaseModel):
    """Scene-level rollup plus the header counters the dashboard shows."""

    project_id: str
    overview: dict[str, Any]
    scenes: list[SceneView]


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


@router.post("/ingest-adapted/{shape}")
def ingest_adapted(shape: str, request: PipelineIngestRequest) -> dict[str, Any]:
    """Ingest a payload in team 1's or team 2's native shape.

    `shape` is `script`, `footage`, `call_sheet` or `auto`. With `auto` the
    shape is detected from the payload, which is what the upload endpoints and
    the vision service use.
    """
    source = request.source or _SHAPE_SOURCES.get(shape)
    if shape not in {*_SHAPE_SOURCES, "auto"}:
        valid = ", ".join([*_SHAPE_SOURCES, "auto"])
        raise HTTPException(422, f"Unknown shape '{shape}'. Expected one of: {valid}")

    h = payload_hash(request.payload)
    engine = get_engine(request.project_id)
    if is_duplicate_payload(request.project_id, h):
        return {
            "project_id": request.project_id,
            "facts_ingested": 0,
            "duplicate": True,
            "graph_stats": engine.stats(),
        }

    if shape == "footage" or (shape == "auto" and source is SourceType.FOOTAGE):
        result = ingest_vision_document(
            engine,
            request.project_id,
            request.payload,
            scene_id=request.scene_id,
            entity_aliases=request.entity_aliases,
            analyse=request.analyse,
        )
    else:
        result = ingest_payload(
            engine,
            request.project_id,
            request.payload,
            source=source,
            extractor=request.extractor,
            analyse=request.analyse,
            scene_id=request.scene_id,
            entity_aliases=request.entity_aliases,
        )
    record_payload_hash(request.project_id, h)
    return result.as_dict()


@router.post("/pipeline/run")
def run_pipeline(request: PipelineRunRequest) -> dict[str, Any]:
    """Ingest script, call-sheet and footage payloads in one call, then analyse.

    Ordering matters: intent before observation, so the script and call sheet
    are ingested first and the footage is compared against them.
    """
    engine = get_engine(request.project_id)
    steps: list[dict[str, Any]] = []

    for payload, source in (
        (request.script, SourceType.SCRIPT),
        (request.call_sheet, SourceType.CALL_SHEET),
    ):
        if payload is None:
            continue
        h = payload_hash(payload)
        if is_duplicate_payload(request.project_id, h):
            steps.append({"source": source.value, "duplicate": True, "facts_ingested": 0})
            continue
        result = ingest_payload(engine, request.project_id, payload, source=source)
        record_payload_hash(request.project_id, h)
        steps.append(result.as_dict())

    if request.footage is not None:
        h = payload_hash(request.footage)
        if is_duplicate_payload(request.project_id, h):
            steps.append({"source": "footage", "duplicate": True, "facts_ingested": 0})
        else:
            result = ingest_vision_document(
                engine,
                request.project_id,
                request.footage,
                scene_id=request.scene_id,
                entity_aliases=request.entity_aliases,
            )
            record_payload_hash(request.project_id, h)
            steps.append(result.as_dict())

    if not steps:
        raise HTTPException(422, "Provide at least one of: script, footage, call_sheet.")

    report = engine.analyse()
    scenes = scene_views(engine, report.issues)
    return {
        "project_id": request.project_id,
        "steps": steps,
        "report": report.model_dump(mode="json"),
        "overview": project_overview(engine, scenes),
        "scenes": [s.model_dump(mode="json") for s in scenes],
    }


@router.post("/analyse", response_model=ContinuityReport)
def analyse(request: AnalyseRequest) -> ContinuityReport:
    """Run continuity analysis and return the full report."""
    engine = get_engine(request.project_id)
    return engine.analyse(request.scene_id)


@router.get("/scenes/{project_id}", response_model=ProjectViewResponse)
def list_scenes(project_id: str, analyse: bool = False) -> ProjectViewResponse:
    """Per-scene rollup: what each scene is, what it scored, what went wrong.

    Uses the issues from the last analysis; pass `analyse=true` to re-run
    detection first.
    """
    engine = get_engine(project_id)
    issues = engine.analyse().issues if analyse else engine.issues()
    scenes = scene_views(engine, issues)
    return ProjectViewResponse(
        project_id=project_id,
        overview=project_overview(engine, scenes),
        scenes=scenes,
    )


@router.get("/entities/{project_id}", response_model=list[EntityView])
def list_entities(
    project_id: str,
    entity_type: str | None = None,
    attribute: str | None = None,
) -> list[EntityView]:
    """Expected vs observed state per entity attribute, per scene.

    `entity_type=character` / `entity_type=prop` and `attribute=wears` narrow
    the result for the costume and prop tracking screens. Both accept
    comma-separated lists.
    """
    engine = get_engine(project_id)
    return entity_views(
        engine,
        engine.issues(),
        entity_types=_csv(entity_type),
        attributes=_csv(attribute),
    )


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
