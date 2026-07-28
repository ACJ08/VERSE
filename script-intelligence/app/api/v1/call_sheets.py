"""
VERSE API v1 - Production Call Sheet Endpoints.
"""

from fastapi import APIRouter, File, UploadFile
from app.services.call_sheet_service import CallSheetService
from app.schemas.responses import CallSheetResponse

router = APIRouter(tags=["Production Call Sheets"])


@router.post(
    "/parse-call-sheet",
    response_model=CallSheetResponse,
    summary="Parse a production call sheet",
    description="Upload a production call sheet (PDF, DOCX, TXT), extract text, and parse production metadata.",
)
async def parse_call_sheet_endpoint(
    file: UploadFile = File(..., description="Call sheet document file (PDF, DOCX, TXT)."),
) -> CallSheetResponse:
    """Call sheet parsing pipeline endpoint."""
    return CallSheetService.process_call_sheet_pipeline(file)
