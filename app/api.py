"""
VERSE – Continuity Script Intelligence
app/api.py

FastAPI APIRouter that exposes all VERSE endpoints.

Endpoints
---------
GET  /health
    Liveness probe + Granite configuration status.

POST /upload-script
    Save a screenplay file to disk, return the saved path.

POST /parse-script
    Upload → extract text → split scenes → return scene list.

POST /analyse-script
    Full pipeline: upload → extract → split → Granite analysis →
    return structured ``SceneContinuity`` JSON for every scene.

POST /analyse-scene
    Accept raw scene text in the request body and return a single
    ``SceneContinuity`` object (useful for incremental / streaming
    workflows).

POST /parse-call-sheet
    Upload → extract text → parse call-sheet metadata.

Design notes
------------
* All file I/O uses helpers from ``app.utils`` so error handling is
  consistent and not duplicated across routes.
* Granite calls are wrapped in a per-scene try/except so that one bad
  scene does not abort analysis of the entire script.
* Response models are declared in each route's ``response_model``
  parameter so FastAPI generates accurate OpenAPI documentation.
"""

from __future__ import annotations

import logging
import os
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app._version import __version__
from app.call_sheet import parse_call_sheet
from app.granite import analyse_scene as granite_analyse_scene
from app.granite import is_granite_configured
from app.schema import (
    AnalyseSceneRequest,
    AnalyseScriptResponse,
    ContinuityNote,
    HealthResponse,
    ParseScriptResponse,
    SceneContinuity,
    SceneMetadata,
)
from app.scene_splitter import split_into_scenes
from app.utils import clean_screenplay_text, extract_text, save_upload, save_extracted_text

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Storage directories (mirrors main.py so both routers agree on layout)
# ---------------------------------------------------------------------------
_SCRIPT_UPLOAD_DIR = "uploads/scripts"
_CALL_SHEET_UPLOAD_DIR = "uploads/call_sheets"
_SCRIPT_EXTRACT_DIR = "extracted/scripts"
_CALL_SHEET_EXTRACT_DIR = "extracted/call_sheets"

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(tags=["VERSE Continuity API"])


# ===========================================================================
# GET /health
# ===========================================================================

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="API health check",
    description=(
        "Returns the API status, version string, and whether the local IBM Granite "
        "integration layer is configured."
    ),
)
def health_check() -> HealthResponse:
    """Liveness probe – always returns 200 while the process is running."""
    return HealthResponse(
        status="ok",
        version=__version__,
        granite_configured=is_granite_configured(),
    )


# ===========================================================================
# POST /upload-script
# ===========================================================================

@router.post(
    "/upload-script",
    summary="Upload a screenplay file",
    description=(
        "Save a screenplay document (PDF, DOCX, or TXT) to disk. "
        "Returns the path where the file was persisted."
    ),
)
async def upload_script(
    file: UploadFile = File(..., description="Screenplay file (PDF, DOCX, or TXT)."),
) -> dict:
    """
    Upload a screenplay file without triggering text extraction or analysis.

    Use this when you want to stage a file before calling ``/parse-script``
    or ``/analyse-script``.
    """
    saved_path = save_upload(file, _SCRIPT_UPLOAD_DIR)
    return {
        "message": "Script uploaded successfully.",
        "filename": file.filename,
        "path": saved_path,
    }


# ===========================================================================
# POST /parse-script
# ===========================================================================

@router.post(
    "/parse-script",
    response_model=ParseScriptResponse,
    summary="Extract text and split a screenplay into scenes",
    description=(
        "Upload a screenplay (PDF, DOCX, TXT), extract its full text, "
        "split it into individual scenes by INT./EXT. headings, and save "
        "the extracted text. Returns the scene count and a preview of the "
        "first scene."
    ),
)
async def parse_script(
    file: UploadFile = File(..., description="Screenplay file (PDF, DOCX, or TXT)."),
) -> ParseScriptResponse:
    """
    Document pipeline: upload → extract → split → structured scene list.

    No AI analysis is performed.  Use ``/analyse-script`` for full
    Granite-powered continuity extraction.
    """
    # 1. Save upload to disk
    file_path = save_upload(file, _SCRIPT_UPLOAD_DIR)

    # 2. Extract plain text
    raw_text = extract_text(file_path)

    # 3. Clean & normalise
    clean_text = clean_screenplay_text(raw_text)

    # 4. Persist extracted text
    extracted_path = save_extracted_text(
        text=clean_text,
        destination_dir=_SCRIPT_EXTRACT_DIR,
        base_filename=file.filename or "script",
    )

    # 5. Split into scenes
    scenes: List[str] = split_into_scenes(clean_text)

    return ParseScriptResponse(
        filename=file.filename or "unknown",
        scene_count=len(scenes),
        extracted_text_path=extracted_path,
        first_scene_preview=scenes[0][:500] if scenes else None,
    )


# ===========================================================================
# POST /analyse-script
# ===========================================================================

@router.post(
    "/analyse-script",
    response_model=AnalyseScriptResponse,
    summary="Full AI-powered script continuity analysis",
    description=(
        "Upload a screenplay, extract text, split into scenes, then send each "
        "scene to local IBM Granite 4.1 for structured continuity "
        "extraction (characters, props, lighting, continuity notes). "
        "Returns a JSON array of ``SceneContinuity`` objects."
    ),
)
async def analyse_script(
    file: UploadFile = File(..., description="Screenplay file (PDF, DOCX, or TXT)."),
) -> AnalyseScriptResponse:
    """
    Full pipeline: upload → extract → split → Granite per-scene analysis.

    Granite errors for individual scenes are captured as
    ``ContinuityNote`` warnings so partial failures do not abort the
    entire response.
    """
    # 0. Guard: configuration must be present before we start any I/O
    if not is_granite_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Local Granite server is not configured. "
                "Set GRANITE_BASE_URL and GRANITE_MODEL in your environment."
            ),
        )

    # 1. Save upload to disk
    file_path = save_upload(file, _SCRIPT_UPLOAD_DIR)

    # 2. Extract + clean text
    raw_text = extract_text(file_path)
    clean_text = clean_screenplay_text(raw_text)

    # 3. Persist extracted text
    save_extracted_text(
        text=clean_text,
        destination_dir=_SCRIPT_EXTRACT_DIR,
        base_filename=file.filename or "script",
    )

    # 4. Split into scenes
    scene_texts: List[str] = split_into_scenes(clean_text)
    if not scene_texts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No scenes detected in the uploaded document. "
                   "Ensure the screenplay uses INT. / EXT. scene headings.",
        )

    # 5. Analyse each scene with Granite (collect errors non-fatally)
    analysed_scenes: List[SceneContinuity] = []
    errors: List[str] = []

    for idx, scene_text in enumerate(scene_texts, start=1):
        scene_id = f"SCENE_{idx:03d}"
        try:
            result: SceneContinuity = granite_analyse_scene(
                scene_text=scene_text,
                scene_id=scene_id,
            )
            analysed_scenes.append(result)
        except Exception as exc:  # noqa: BLE001
            error_msg = f"{scene_id}: {exc}"
            logger.warning("Granite analysis failed for %s – %s", scene_id, exc)
            errors.append(error_msg)

            # Insert a placeholder scene so scene count stays consistent
            analysed_scenes.append(
                SceneContinuity(
                    metadata=SceneMetadata(
                        scene_id=scene_id,
                        heading=scene_text.strip().splitlines()[0][:120]
                        if scene_text.strip()
                        else None,
                    ),
                    continuity_notes=[
                        ContinuityNote(
                            note=f"Granite analysis failed: {exc}",
                            severity="HIGH",
                            category="OTHER",
                        )
                    ],
                )
            )

    return AnalyseScriptResponse(
        filename=file.filename or "unknown",
        scene_count=len(scene_texts),
        scenes=analysed_scenes,
        errors=errors,
    )


# ===========================================================================
# POST /analyse-scene
# ===========================================================================

@router.post(
    "/analyse-scene",
    response_model=SceneContinuity,
    summary="Analyse a single screenplay scene",
    description=(
        "Accept the raw text of a single scene in the request body and return "
        "a structured ``SceneContinuity`` object produced by local IBM Granite 4.1. "
        "Useful for incremental or streaming workflows where scenes are sent "
        "one at a time."
    ),
)
async def analyse_scene_endpoint(
    request: AnalyseSceneRequest,
) -> SceneContinuity:
    """
    Stateless single-scene analysis endpoint.

    Accepts JSON body with ``scene_text`` and optional ``scene_id`` fields.
    """
    if not is_granite_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Local Granite server is not configured. "
                "Set GRANITE_BASE_URL and GRANITE_MODEL in your environment."
            ),
        )

    scene_id = request.scene_id or "SCENE_01"

    try:
        result = granite_analyse_scene(
            scene_text=request.scene_text,
            scene_id=scene_id,
        )
    except RuntimeError as exc:
        # Connectivity / server failures → 503
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to connect to Granite inference server: {exc}",
        ) from exc
    except ValueError as exc:
        # JSON parsing failure → 502 (bad upstream response)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Granite response parse error: {exc}",
        ) from exc

    return result


# ===========================================================================
# POST /parse-call-sheet
# ===========================================================================

@router.post(
    "/parse-call-sheet",
    summary="Parse a production call sheet",
    description=(
        "Upload a call sheet (PDF, DOCX, or TXT), extract its text, and "
        "parse production metadata including date, director, location, "
        "shoot time, scenes, cast, and crew."
    ),
)
async def parse_call_sheet_endpoint(
    file: UploadFile = File(..., description="Call sheet file (PDF, DOCX, or TXT)."),
) -> dict:
    """
    Call sheet pipeline: upload → extract → parse → structured JSON.

    Returns the raw extracted text path alongside the parsed metadata dict
    so that downstream systems can re-process if needed.
    """
    # 1. Save upload
    file_path = save_upload(file, _CALL_SHEET_UPLOAD_DIR)

    # 2. Extract text
    raw_text = extract_text(file_path)

    # 3. Persist extracted text
    extracted_path = save_extracted_text(
        text=raw_text,
        destination_dir=_CALL_SHEET_EXTRACT_DIR,
        base_filename=file.filename or "call_sheet",
    )

    # 4. Parse call sheet metadata
    try:
        call_sheet_data = parse_call_sheet(raw_text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Call sheet parsing failed for '%s'.", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Call sheet parsing error: {exc}",
        ) from exc

    return {
        "filename": file.filename,
        "uploaded_path": file_path,
        "extracted_path": extracted_path,
        "call_sheet": call_sheet_data,
    }