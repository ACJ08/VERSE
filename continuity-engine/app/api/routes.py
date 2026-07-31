"""FastAPI router for the continuity engine.

This module is a thin HTTP shell over ContinuityEngine — it owns no business
logic. All detection, scoring, and reporting happens inside the engine itself
so the engine stays usable as a pure Python library without FastAPI.

Endpoint overview
-----------------
Classic ingest (raw engine format):
    POST /continuity/ingest/script          — structured script JSON
    POST /continuity/ingest/footage         — structured footage JSON
    POST /continuity/ingest/{source}        — any source type (call sheet, notes, …)

Pipeline ingest (native team shapes):
    POST /continuity/ingest-adapted/{shape} — team 1 or team 2 payload, auto-adapted
    POST /continuity/pipeline/run           — script + footage + call-sheet in one call

Analysis & views:
    POST /continuity/analyse                — run full analysis, return ContinuityReport
    GET  /continuity/scenes/{project_id}    — per-scene score rollup for the dashboard
    GET  /continuity/entities/{project_id}  — per-entity expected-vs-observed state

Human feedback:
    GET  /continuity/issues/{project_id}    — current issues (no re-run)
    POST /continuity/feedback               — confirm / dismiss / resolve / reopen
    POST /continuity/facts/override         — human fact correction (outranks AI)

System:
    GET  /continuity/health                 — engine health + active project list

Mounting:
    from app.api.routes import router
    app.include_router(router)   # in main.py
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Share the engine registry with the projects router — every project_id maps
# to exactly one ContinuityEngine instance across the entire process.
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

# Maps the URL shape parameter to the SourceType the engine uses internally.
# Used by ingest_adapted() to determine how to route a payload.
_SHAPE_SOURCES: dict[str, SourceType] = {
    "script": SourceType.SCRIPT,
    "footage": SourceType.FOOTAGE,
    "call_sheet": SourceType.CALL_SHEET,
}


def _csv(value: str | None) -> set[str] | None:
    """Parse a comma-separated query string into a filter set, or None for 'no filter'.

    Example: "character,prop" → {"character", "prop"}
    """
    if not value:
        return None
    parts = {part.strip() for part in value.split(",") if part.strip()}
    return parts or None


# ─── Request models ───────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    """Classic ingest — payload must already be in the engine's internal format."""
    project_id: str = "VERSE_DEMO"
    payload: Any = Field(..., description="Arbitrary nested JSON from the producing team")
    extractor: str | None = None  # Hint about which extractor produced the payload


class AnalyseRequest(BaseModel):
    """Request to run continuity analysis, optionally scoped to one scene."""
    project_id: str = "VERSE_DEMO"
    scene_id: str | None = None  # Omit to analyse the whole project


class FeedbackRequest(BaseModel):
    """Human decision on a detected continuity issue."""
    project_id: str = "VERSE_DEMO"
    action: FeedbackAction  # issue_id + action ("confirm"|"dismiss"|"resolve"|"reopen") + optional note


class OverrideRequest(BaseModel):
    """Human fact correction — overwrites the AI-produced value for one attribute."""
    project_id: str = "VERSE_DEMO"
    override: FactOverride  # entity_key + attribute + new value


class IngestResponse(BaseModel):
    """Minimal response returned by the classic ingest endpoints."""
    project_id: str
    facts_ingested: int   # Number of new facts added to the graph (0 on duplicate)
    stats: dict[str, int] # Live graph stats: nodes, edges, facts, scenes, entities


class PipelineIngestRequest(BaseModel):
    """Ingest a payload in a producing team's native shape.

    The payload is run through app/adapters/ first, so team 1 can POST their
    AnalyseScriptResponse and team 2 can POST a vision scene document without
    reshaping their output to the engine's internal format.
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
        None, description="Override the source type implied by the payload shape"
    )
    extractor: str | None = None
    analyse: bool = Field(False, description="Run analysis after ingest and include the report")


class PipelineRunRequest(BaseModel):
    """Ingest script, call-sheet and footage payloads together, then analyse.

    Ordering inside the handler is fixed: script → call_sheet → footage, which
    matches the production lifecycle (intent before observation).
    """
    project_id: str = "VERSE_DEMO"
    script: Any | None = None       # Team 1 screenplay payload
    footage: Any | None = None      # Team 2 vision scene document
    call_sheet: Any | None = None   # Team 1 call-sheet payload
    scene_id: str | None = None     # Scene context for footage
    entity_aliases: dict[str, Any] | None = None  # Vision id → character name map


class ProjectViewResponse(BaseModel):
    """Per-scene rollup plus the header counters shown in the dashboard."""
    project_id: str
    overview: dict[str, Any]   # ProjectOverview — total scenes, issues, score, …
    scenes: list[SceneView]    # One SceneView per detected scene


# ─── Classic ingest endpoints ────────────────────────────────────────────────

@router.post("/ingest/script", response_model=IngestResponse)
def ingest_script(request: IngestRequest) -> IngestResponse:
    """Accept structured script JSON from team 1 in the engine's native format.

    Duplicate payloads are detected by SHA-256 hash and silently skipped with
    facts_ingested=0 so the client can safely retry on network errors.
    """
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
    """Accept structured footage observations from team 2 in the engine's native format.

    Duplicate detection works the same way as ingest_script.
    """
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
    """Accept any payload with an explicit source type (call sheets, production notes, etc.)."""
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


# ─── Pipeline ingest endpoints ───────────────────────────────────────────────

@router.post("/ingest-adapted/{shape}")
def ingest_adapted(shape: str, request: PipelineIngestRequest) -> dict[str, Any]:
    """Ingest a payload in team 1's or team 2's native output shape.

    The `shape` parameter tells the adapter which format to expect:
    - "script"     → team 1's AnalyseScriptResponse
    - "footage"    → team 2's vision scene document
    - "call_sheet" → team 1's call-sheet parser output
    - "auto"       → detect shape from the payload structure

    The adapter in app/adapters/ normalises the payload before it reaches
    the engine, so neither team needs to change their output format.
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

    # Route footage through the vision-specific path which handles frame
    # aggregation and entity alias resolution before standard ingest.
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
    """Ingest script, call-sheet and footage in one atomic call, then analyse.

    Ordering is fixed: script → call_sheet → footage. This ensures the engine
    always sees intent (what was planned) before observation (what was filmed),
    which is the only order that produces meaningful continuity comparisons.
    At least one of script / footage / call_sheet must be provided.
    """
    engine = get_engine(request.project_id)
    steps: list[dict[str, Any]] = []

    # Process intent sources first (screenplay and call-sheet)
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

    # Process observation source last (footage)
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

    # Run analysis after all data is ingested so the report sees the full picture
    report = engine.analyse()
    scenes = scene_views(engine, report.issues)
    return {
        "project_id": request.project_id,
        "steps": steps,
        "report": report.model_dump(mode="json"),
        "overview": project_overview(engine, scenes),
        "scenes": [s.model_dump(mode="json") for s in scenes],
    }


# ─── Analysis ─────────────────────────────────────────────────────────────────

@router.post("/analyse", response_model=ContinuityReport)
def analyse(request: AnalyseRequest) -> ContinuityReport:
    """Run continuity analysis and return the full scored report.

    Passing scene_id restricts detection to that scene and is faster.
    Omitting it analyses the whole project and is the most complete.
    Re-running is always safe — the detector resets its counters each pass.
    """
    engine = get_engine(request.project_id)
    return engine.analyse(request.scene_id)


# ─── Dashboard views ─────────────────────────────────────────────────────────

@router.get("/scenes/{project_id}", response_model=ProjectViewResponse)
def list_scenes(project_id: str, analyse: bool = False) -> ProjectViewResponse:
    """Per-scene rollup used by the Scene Tracking and Timeline pages.

    Returns one SceneView per detected scene: score, issue counts by severity,
    entities present, whether footage has been uploaded, and a human-readable
    headline. Pass ?analyse=true to re-run detection first.
    """
    engine = get_engine(project_id)
    # Use the last cached analysis unless the caller explicitly requests a fresh run
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
    """Per-entity tracking state used by Costume, Prop, and Character Tracking pages.

    Each EntityView contains all attribute slots for one entity:
    expected value (from screenplay), observed value (from footage), slot state
    (match / conflict / unverified / observed_only), and any linked issue.

    Query params accept comma-separated lists:
        ?entity_type=character          → characters only
        ?entity_type=character,prop     → both
        ?attribute=wears,holds          → specific attributes only
    """
    engine = get_engine(project_id)
    return entity_views(
        engine,
        engine.issues(),
        entity_types=_csv(entity_type),
        attributes=_csv(attribute),
    )


# ─── Issues & feedback ───────────────────────────────────────────────────────

@router.get("/issues/{project_id}", response_model=list[Issue])
def list_issues(project_id: str) -> list[Issue]:
    """Return current issues from the last analysis run without triggering a new one.

    Used by the AI Recommendations panel on the Producer dashboard.
    """
    return get_engine(project_id).issues()


@router.post("/feedback", response_model=Issue)
def submit_feedback(request: FeedbackRequest) -> Issue:
    """Record a human decision on a continuity issue.

    Actions:
    - confirm  → human verified the issue is real; increases confidence
    - dismiss  → human says it is not an error; pattern is suppressed in future runs
    - resolve  → issue has been fixed in production; marked resolved
    - reopen   → revert a previous dismiss or resolve

    The updated Issue is returned immediately. Call /analyse again to see the
    refreshed score that reflects the new human decision.
    """
    engine = get_engine(request.project_id)
    issue = engine.apply_feedback(request.action)
    if issue is None:
        raise HTTPException(404, f"Unknown issue '{request.action.issue_id}'")
    return issue


@router.post("/facts/override")
def override_fact(request: OverrideRequest) -> dict[str, Any]:
    """Record a human fact correction that outranks all AI-produced facts.

    Use this when the screenplay or footage extraction produced a wrong value
    and you want to pin the correct one (e.g. the script says 'navy jacket'
    but the costume designer knows it was changed to 'charcoal grey').
    """
    engine = get_engine(request.project_id)
    fact = engine.override_fact(request.override)
    return {"fact_id": fact.fact_id, "value": fact.value, "human_confirmed": True}


# ─── Health ───────────────────────────────────────────────────────────────────

@router.get("/health")
def health() -> dict[str, Any]:
    """Return engine health and the list of project IDs currently in the cache.

    Used by the dev dashboard and monitoring. An empty projects list means no
    data has been ingested in this process lifetime (normal after a restart).
    """
    from app.api.projects import _ENGINES
    return {"status": "ok", "projects": list(_ENGINES)}
