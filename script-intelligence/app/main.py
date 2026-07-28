"""
VERSE – Continuity Script Intelligence Application Entrypoint.
"""

from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI, UploadFile, File, Request, status
from fastapi.responses import JSONResponse

from app._version import __version__
from app.core.config import settings
from app.core.errors import VERSEError
from app.core.logging import setup_logging, get_logger
from app.api import router as verse_router
from app.services.script_service import ScriptService
from app.services.call_sheet_service import CallSheetService

# Configure logging
setup_logging()
logger = get_logger("app.main")

# Initialize FastAPI Application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "AI-powered screenplay and production document intelligence system for film continuity workflows. "
        "Part of the VERSE (Visual & Explainable Reasoning for Semantic Evolution) ecosystem."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Exception Handler for Domain VERSE errors (sanitizes output, suppresses raw stack traces)
@app.exception_handler(VERSEError)
async def verse_error_handler(request: Request, exc: VERSEError) -> JSONResponse:
    logger.warning("VERSE domain error on %s %s: %s", request.method, request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Please consult server logs.",
        },
    )


# Mount structured API Router under /api/v1
app.include_router(verse_router, prefix=settings.API_V1_STR)


# Create default upload directories
for folder in [
    settings.SCRIPT_UPLOAD_DIR,
    settings.CALL_SHEET_UPLOAD_DIR,
    settings.SCRIPT_EXTRACT_DIR,
    settings.CALL_SHEET_EXTRACT_DIR,
]:
    os.makedirs(folder, exist_ok=True)


@app.get("/", summary="Root status check")
def root() -> dict:
    return {
        "status": "running",
        "message": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
    }


# ---------------------------------------------------------------------------
# Legacy Endpoint Compatibility (Root level paths)
# ---------------------------------------------------------------------------

@app.post("/upload-script", tags=["Legacy Compatibility"])
async def upload_script_legacy(file: UploadFile = File(...)):
    res = ScriptService.process_script_upload(file)
    return {
        "message": res.message,
        "filename": res.filename,
        "path": res.path,
    }


@app.post("/parse-script", tags=["Legacy Compatibility"])
async def parse_script_legacy(file: UploadFile = File(...)):
    res = ScriptService.parse_script_pipeline(file)
    return {
        "filename": res.filename,
        "scene_count": res.scene_count,
        "extracted_text": res.extracted_text_path,
        "first_scene": res.first_scene_preview or "",
    }


@app.post("/parse-call-sheet", tags=["Legacy Compatibility"])
async def parse_call_sheet_legacy(file: UploadFile = File(...)):
    res = CallSheetService.process_call_sheet_pipeline(file)
    return {
        "filename": res.filename,
        "uploaded_path": res.uploaded_path,
        "extracted_path": res.extracted_path,
        "call_sheet": res.call_sheet.model_dump(),
    }