"""
VERSE API v1 - Screenplay Endpoints.
"""

from fastapi import APIRouter, File, UploadFile

from app.services.script_service import ScriptService
from app.services.continuity_service import ContinuityService
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
