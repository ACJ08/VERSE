"""
VERSE Services - Script Continuity Orchestration Service.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple
from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import InferenceError, ParsingError
from app.core.logging import get_logger, timed_execution
from app.llm.granite_client import get_client, is_granite_configured
from app.parsers.document_parser import extract_text
from app.parsers.scene_splitter import split_into_scenes, parse_scene_metadata
from app.utils.file_utils import save_upload, save_extracted_text
from app.utils.text_utils import clean_screenplay_text, extract_action_prose
from app.schemas.continuity import SceneContinuity, ContinuityNote
from app.schemas.responses import AnalyseScriptResponse

logger = get_logger(__name__)


class ContinuityService:
    """Service orchestrating full script continuity analysis and parallel LLM inference."""

    @staticmethod
    def analyse_script_pipeline(file: UploadFile) -> AnalyseScriptResponse:
        """
        Full pipeline: Upload -> Extract -> Split -> Parallel Granite Scene Analysis.
        """
        if not is_granite_configured():
            raise InferenceError(
                "Local Granite server is not configured. Set GRANITE_BASE_URL and GRANITE_MODEL in environment.",
                status_code=503,
            )

        # 1. Save upload
        file_path = save_upload(file, settings.SCRIPT_UPLOAD_DIR)

        # 2. Extract + clean text
        raw_text = extract_text(file_path)
        clean_text = clean_screenplay_text(raw_text)

        # 3. Persist extracted text
        save_extracted_text(
            text=clean_text,
            destination_dir=settings.SCRIPT_EXTRACT_DIR,
            base_filename=file.filename or "script",
        )

        # 4. Split into scenes
        scene_texts: List[str] = split_into_scenes(clean_text)
        if not scene_texts:
            raise ParsingError("No scenes detected in the uploaded screenplay.")

        # 5. Parallel scene analysis using ThreadPoolExecutor
        analysed_scenes: List[SceneContinuity] = [None] * len(scene_texts)  # Pre-allocate to keep order
        errors: List[str] = []

        client = get_client()
        max_workers = min(settings.MAX_PARALLEL_SCENE_ANALYSES, len(scene_texts))

        def _worker(index: int, scene_txt: str) -> Tuple[int, SceneContinuity, str]:
            scene_id = f"SCENE_{index + 1:03d}"
            try:
                result = client.analyse_scene(scene_text=scene_txt, scene_id=scene_id)
                return index, result, ""
            except Exception as exc:
                logger.warning("Granite analysis failed for %s – %s", scene_id, exc)
                # Return placeholder error scene
                placeholder = SceneContinuity(
                    metadata=parse_scene_metadata(scene_text=scene_txt, scene_id=scene_id),
                    continuity_notes=[
                        ContinuityNote(
                            note=f"Granite analysis failed: {exc}",
                            severity="HIGH",
                            category="OTHER",
                        )
                    ],
                    confidence_score=0.0,
                    # Entities could not be extracted, but the action prose still
                    # lets downstream reasoning place the scene and read its events.
                    action=extract_action_prose(scene_txt),
                )
                return index, placeholder, f"{scene_id}: {exc}"

        with timed_execution(f"Full script continuity analysis ({len(scene_texts)} scenes)", logger):
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(_worker, idx, scene_txt)
                    for idx, scene_txt in enumerate(scene_texts)
                ]
                for future in as_completed(futures):
                    idx, res, err_msg = future.result()
                    analysed_scenes[idx] = res
                    if err_msg:
                        errors.append(err_msg)

        return AnalyseScriptResponse(
            filename=file.filename or "unknown",
            scene_count=len(scene_texts),
            scenes=analysed_scenes,
            errors=errors,
        )
