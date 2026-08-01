"""Document upload endpoints — screenplays, call sheets and footage.

Each endpoint runs the same three steps: get structured JSON out of the file,
adapt it to the engine's contract, ingest it. Only the first step differs.

Screenplay extraction, in order of preference:
1. **Team 1's Script Intelligence service** (`SCRIPT_SERVICE_URL`) — Granite
   extraction of characters, props, wardrobe, lighting and continuity notes.
   This is the richest source and the one the pipeline is designed around.
2. **Local Granite via watsonx** (`WATSONX_API_KEY`) — scenes, characters and
   props only.
3. **Regex/heuristic parser** — standard INT./EXT. headings, no AI required.

Footage extraction:
1. A vision **scene document** uploaded as JSON (what `vision_pipeline/main.py`
   writes) — no heavy vision dependencies needed in this service.
2. A **video clip**, forwarded to team 2's service (`VISION_SERVICE_URL`) which
   runs detection and returns that same document.

Every step degrades rather than fails: an offline sibling service falls through
to the next option, and the response says which path ran.
"""

from __future__ import annotations

import json
import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.adapters import adapt_call_sheet, adapt_script_intelligence
from app.api.projects import (
    get_or_create_engine,
    is_duplicate_payload,
    payload_hash,
    record_payload_hash,
)
from app.core.dependencies import get_current_user
from app.models.schemas import SourceType
from app.reporting.views import project_overview, scene_views
from app.services.pipeline import (
    UpstreamUnavailable,
    ingest_payload,
    ingest_vision_document,
    script_service,
    vision_service,
)

router = APIRouter(prefix="/upload", tags=["upload"])

_ALLOWED = {
    "application/pdf", "text/plain",
    "application/octet-stream",
    "text/x-fountain", "application/xml",
}
_MAX_SIZE_MB = 20
_MAX_VIDEO_SIZE_MB = 200


def _extract_text(filename: str, data: bytes) -> str:
    """Extract plain text from uploaded screenplay."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            raise HTTPException(
                422,
                "PDF parsing requires pypdf. Install it: pip install pypdf. "
                "Alternatively upload a .txt or .fountain file."
            )
    try:
        return data.decode("utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(422, f"Could not read file: {exc}")


# ─── Granite-based extractor ──────────────────────────────────────────────────

def _granite_extract(text: str, project_id: str) -> dict | None:
    """
    Use IBM Granite to extract structured scenes from raw screenplay text.
    Supports both the IBM watsonx cloud API and a local llama-cpp-python server.
    Returns a script-JSON dict on success, or None if Granite is unavailable.
    """
    try:
        from app.services.watsonx import create_llm
        llm = create_llm()
        if llm is None:
            return None
    except ImportError:
        return None

    # Truncate to avoid token limits — first 8000 chars covers ~40 scenes
    excerpt = text[:8000]

    prompt = f"""You are a screenplay analysis assistant. Extract structured scene data from the screenplay excerpt below.

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{{
  "scenes": [
    {{
      "scene_id": "SCENE_001",
      "sequence": 1,
      "location": "<INT/EXT location - time>",
      "time_of_day": "<DAY|NIGHT|DUSK|DAWN>",
      "action": "<brief action description, max 300 chars>",
      "characters": [
        {{"name": "<CHARACTER NAME>", "type": "character"}}
      ],
      "props": [
        {{"name": "<prop name>", "type": "prop"}}
      ]
    }}
  ]
}}

Rules:
- scene_id must be SCENE_001, SCENE_002, etc.
- sequence must be an integer starting at 1
- characters: only characters who appear in the scene
- props: only objects explicitly mentioned in the action
- If uncertain, omit the field rather than guessing

SCREENPLAY:
{excerpt}

JSON:"""

    raw = llm(prompt)
    if not raw:
        return None

    # Extract the JSON block from the response (LLM may include surrounding text)
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        return None

    try:
        import json
        result = json.loads(json_match.group())
        if isinstance(result.get("scenes"), list) and result["scenes"]:
            result["project_id"] = project_id
            result["source"] = "script"
            return result
    except (ValueError, KeyError):
        pass

    return None


# ─── Heuristic fallback parser ────────────────────────────────────────────────

def _heuristic_extract(text: str, project_id: str) -> dict:
    """
    Regex/heuristic screenplay → structured JSON.
    Handles standard INT./EXT. headings.
    Used when Granite is unavailable.
    """
    scenes = []
    heading_re = re.compile(
        r"^(INT\.|EXT\.|I/E\.|INT/EXT\.)[^\n]+", re.IGNORECASE | re.MULTILINE
    )
    positions = [m.start() for m in heading_re.finditer(text)] + [len(text)]

    for i, start in enumerate(positions[:-1]):
        end = positions[i + 1]
        block = text[start:end].strip()
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue

        heading = lines[0]
        action_text = " ".join(lines[1:])[:500]

        time_of_day = "DAY"
        for marker in ("NIGHT", "DUSK", "DAWN", "MORNING", "EVENING", "AFTERNOON"):
            if marker in heading.upper():
                time_of_day = marker
                break

        character_names = list({
            ln for ln in lines[1:]
            if ln.isupper() and 2 < len(ln) < 40 and not ln.startswith("(")
        })

        scene_id = f"SCENE_{i + 1:03d}"
        scenes.append({
            "scene_id": scene_id,
            "sequence": i + 1,
            "location": heading,
            "time_of_day": time_of_day,
            "action": action_text,
            "characters": [{"name": n, "type": "character"} for n in character_names],
            "props": [],
        })

    return {"project_id": project_id, "source": "script", "scenes": scenes}


# ─── Extraction chain ─────────────────────────────────────────────────────────


def _extract_script_payload(
    filename: str, data: bytes, project_id: str
) -> tuple[dict, str, list[dict], list[str]]:
    """Structured scenes from a screenplay file.

    Returns `(engine_payload, extractor_name, continuity_notes, warnings)`.
    Tries team 1's service first because it is the only path that extracts
    wardrobe, prop ownership and lighting — the fields most continuity rules
    depend on.
    """
    warnings: list[str] = []

    client = script_service()
    if client.is_configured:
        try:
            response = client.analyse_script(filename, data)
        except UpstreamUnavailable as exc:
            warnings.append(f"{exc} Fell back to local extraction.")
        else:
            adapted = adapt_script_intelligence(response)
            warnings.extend(adapted.warnings)
            for message in response.get("errors") or []:
                warnings.append(f"Script service: {message}")
            return adapted.payload, "script-intelligence/granite", adapted.notes, warnings

    text = _extract_text(filename, data)
    granite = _granite_extract(text, project_id)
    if granite is not None:
        return granite, "watsonx/granite", [], warnings

    warnings.append(
        "No Granite extraction available — used the heuristic screenplay parser, "
        "which finds scenes and characters but no wardrobe or props."
    )
    return _heuristic_extract(text, project_id), "heuristic", [], warnings


def _scenes_of(payload: dict) -> list:
    return payload.get("scenes") or []


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/screenplay")
async def upload_screenplay(
    current_user: Annotated[dict, Depends(get_current_user)],
    project_id: str = Form(...),
    file: UploadFile = File(...),
    analyse: bool = Form(False),
):
    """Upload a screenplay, extract it, ingest it, optionally analyse it."""
    if file.size and file.size > _MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {_MAX_SIZE_MB} MB limit.")

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Uploaded file is empty.")

    filename = file.filename or "script.txt"
    script_json, extractor, notes, warnings = _extract_script_payload(filename, data, project_id)

    if not _scenes_of(script_json):
        raise HTTPException(
            422,
            "No scene headings found. Ensure the file uses standard screenplay format "
            "(INT./EXT. headings). You can also use the JSON ingest endpoint directly."
        )

    engine = get_or_create_engine(project_id)
    result = ingest_payload(
        engine,
        project_id,
        script_json,
        source=SourceType.SCRIPT,
        extractor=extractor,
        analyse=analyse,
    )
    result.notes = notes
    result.warnings = warnings + result.warnings

    response = result.as_dict()
    response["filename"] = filename
    # `scenes_detected` counts what the extractor found, which is what the
    # upload banner reports; adapted scene ids can be fewer if some were unusable.
    response["scenes_detected"] = len(_scenes_of(script_json))
    return response


@router.post("/call-sheet")
async def upload_call_sheet(
    current_user: Annotated[dict, Depends(get_current_user)],
    project_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Upload a call sheet. Requires team 1's parser (`SCRIPT_SERVICE_URL`)."""
    if file.size and file.size > _MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {_MAX_SIZE_MB} MB limit.")

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Uploaded file is empty.")

    client = script_service()
    if not client.is_configured:
        raise HTTPException(
            503,
            "Call-sheet parsing needs the Script Intelligence service. "
            "Set SCRIPT_SERVICE_URL, or POST the parsed JSON to "
            "/continuity/ingest-adapted/call_sheet.",
        )
    try:
        response = client.parse_call_sheet(file.filename or "call_sheet.pdf", data)
    except UpstreamUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc

    adapted = adapt_call_sheet(response)
    engine = get_or_create_engine(project_id)
    result = ingest_payload(
        engine,
        project_id,
        adapted.payload,
        source=SourceType.CALL_SHEET,
        extractor="call-sheet-parser",
    )
    result.warnings = adapted.warnings + result.warnings
    result.entities = adapted.entities

    out = result.as_dict()
    out["filename"] = file.filename
    out["call_sheet"] = response.get("call_sheet", response)
    return out


@router.post("/footage")
async def upload_footage(
    current_user: Annotated[dict, Depends(get_current_user)],
    project_id: str = Form(...),
    file: UploadFile = File(...),
    scene_id: str | None = Form(None),
    entity_aliases: str | None = Form(
        None, description='JSON object mapping vision names to script names'
    ),
    analyse: bool = Form(True),
):
    """Upload footage observations for a scene.

    Accepts either the JSON scene document the vision pipeline writes, or a
    video clip which is forwarded to team 2's service when `VISION_SERVICE_URL`
    is configured. Frames are aggregated to one statement per attribute before
    ingestion — see `app/adapters/vision.py`.
    """
    filename = file.filename or "footage.json"
    is_json = filename.lower().endswith(".json") or (file.content_type or "").endswith("json")
    limit = _MAX_SIZE_MB if is_json else _MAX_VIDEO_SIZE_MB
    if file.size and file.size > limit * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {limit} MB limit.")

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Uploaded file is empty.")

    aliases = _parse_aliases(entity_aliases)
    warnings: list[str] = []

    if is_json:
        try:
            payload = json.loads(data.decode("utf-8", errors="replace"))
        except ValueError as exc:
            raise HTTPException(422, f"Could not parse the vision JSON: {exc}") from exc
        extractor = "vision"
    else:
        client = vision_service()
        if not client.is_configured:
            raise HTTPException(
                503,
                "Video processing needs the Vision service. Set VISION_SERVICE_URL, "
                "or upload the scene_<id>.json that vision_pipeline/main.py writes.",
            )
        if not scene_id:
            raise HTTPException(422, "scene_id is required when uploading a video clip.")
        try:
            payload = client.process_clip(filename, data, scene_id)
        except UpstreamUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        extractor = "vision-service"

    engine = get_or_create_engine(project_id)
    h = payload_hash(payload)
    if is_duplicate_payload(project_id, h):
        return {
            "project_id": project_id,
            "filename": filename,
            "duplicate": True,
            "facts_ingested": 0,
            "graph_stats": engine.stats(),
        }

    result = ingest_vision_document(
        engine,
        project_id,
        payload,
        scene_id=scene_id,
        entity_aliases=aliases,
        analyse=analyse,
    )
    record_payload_hash(project_id, h)
    result.extractor = extractor
    result.warnings = warnings + result.warnings

    out = result.as_dict()
    out["filename"] = filename
    if analyse and result.report is not None:
        scenes = scene_views(engine, result.report.issues)
        out["overview"] = project_overview(engine, scenes)
        out["scenes"] = [s.model_dump(mode="json") for s in scenes]
    return out


def _parse_aliases(raw: str | None) -> dict[str, Any] | None:
    """Read the entity_aliases form field, which arrives as a JSON string."""
    if not raw or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise HTTPException(422, f"entity_aliases must be valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(422, "entity_aliases must be a JSON object.")
    return parsed
