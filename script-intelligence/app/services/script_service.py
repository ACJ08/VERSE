"""
VERSE Services - Screenplay Processing Service.
"""

from typing import List, Tuple
from fastapi import UploadFile

from app.core.config import settings
from app.parsers.document_parser import extract_text
from app.parsers.scene_splitter import split_into_scenes
from app.utils.file_utils import save_upload, save_extracted_text
from app.utils.text_utils import clean_screenplay_text
from app.schemas.responses import ParseScriptResponse, FileUploadResponse


class ScriptService:
    """Service handling screenplay uploads, text extraction, and scene splitting."""

    @staticmethod
    def process_script_upload(file: UploadFile) -> FileUploadResponse:
        """Save screenplay upload file to disk."""
        saved_path = save_upload(file, settings.SCRIPT_UPLOAD_DIR)
        return FileUploadResponse(
            message="Script uploaded successfully.",
            filename=file.filename or "unknown",
            path=saved_path,
        )

    @staticmethod
    def parse_script_pipeline(file: UploadFile) -> ParseScriptResponse:
        """
        Execute document processing pipeline:
        Upload -> Extract Text -> Clean -> Persist -> Split Scenes.
        """
        # 1. Save upload to disk
        file_path = save_upload(file, settings.SCRIPT_UPLOAD_DIR)

        # 2. Extract plain text
        raw_text = extract_text(file_path)

        # 3. Clean & normalise
        clean_text = clean_screenplay_text(raw_text)

        # 4. Persist extracted text
        extracted_path = save_extracted_text(
            text=clean_text,
            destination_dir=settings.SCRIPT_EXTRACT_DIR,
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
