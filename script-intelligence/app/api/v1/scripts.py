"""
VERSE API v1 - Screenplay Endpoints.
"""

from fastapi import APIRouter, File, Form, UploadFile
from typing import Optional

from app.services.script_service import ScriptService
from app.services.continuity_service import ContinuityService
from app.services.ingest_bridge import forward_scenes_to_engine
from app.schemas.responses import FileUploadResponse, ParseScriptResponse, AnalyseScriptResponse

router = APIRouter(tags=["Screenplay Intelligence"])


@router.post(
    "/upload-script",
    response_model=FileUploadResponse,
    summary="Upload a screenplay file",
    description="Persist a screenplay file (PDF, DOCX, TXT) to disk without triggering extraction or analysis.",
)
async def upload_script(
    file: UploadFile = File(..., description="Screenplay document file (PDF, DOCX, TXT)."),
) -> FileUploadResponse:
    """Upload screenplay file endpoint."""
    return ScriptService.process_script_upload(file)


@router.post(
    "/parse-script",
    response_model=ParseScriptResponse,
    summary="Extract text and split screenplay into scenes",
    description="Upload a screenplay, extract text, split into scenes by INT./EXT. headings, and persist extracted text.",
)
async def parse_script(
    file: UploadFile = File(..., description="Screenplay document file (PDF, DOCX, TXT)."),
) -> ParseScriptResponse:
    """Screenplay parsing pipeline endpoint."""
    return ScriptService.parse_script_pipeline(file)


@router.post(
    "/analyse-script",
    response_model=AnalyseScriptResponse,
    summary="Full AI continuity analysis of a screenplay",
    description="Upload a screenplay, extract text, split into scenes, and run parallel local Granite/Ollama continuity analysis.",
)
async def analyse_script(
    file: UploadFile = File(..., description="Screenplay document file (PDF, DOCX, TXT)."),
) -> AnalyseScriptResponse:
    """Full screenplay AI analysis endpoint."""
    return ContinuityService.analyse_script_pipeline(file)


@router.post(
    "/analyse-and-ingest",
    response_model=AnalyseScriptResponse,
    summary="Analyse screenplay and forward results to the continuity engine",
    description=(
        "Run full Granite AI continuity analysis on the uploaded screenplay, then "
        "automatically forward the structured scene data to the continuity-engine's "
        "POST /continuity/ingest/script endpoint. "
        "Pass project_id as a form field (defaults to 'VERSE_DEMO'). "
        "The engine URL is configured via CONTINUITY_ENGINE_URL env var."
    ),
)
async def analyse_and_ingest(
    file: UploadFile = File(..., description="Screenplay document file (PDF, DOCX, TXT)."),
    project_id: Optional[str] = Form(default="VERSE_DEMO", description="Target project ID in the continuity engine."),
) -> AnalyseScriptResponse:
    """Analyse screenplay and ingest structured results into the continuity engine."""
    result = ContinuityService.analyse_script_pipeline(file)

    # Forward analysed scenes to the continuity engine (non-blocking on failure)
    if result.scenes:
        forward_scenes_to_engine(result.scenes, project_id or "VERSE_DEMO")

    return result
