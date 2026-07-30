"""
VERSE Services - Production Call Sheet Service.
"""

from fastapi import UploadFile

from app.core.config import settings
from app.parsers.document_parser import extract_text
from app.parsers.call_sheet_parser import parse_call_sheet_to_model
from app.utils.file_utils import save_upload, save_extracted_text
from app.schemas.responses import CallSheetResponse


class CallSheetService:
    """Service handling production call sheet parsing pipeline."""

    @staticmethod
    def process_call_sheet_pipeline(file: UploadFile) -> CallSheetResponse:
        """
        Execute call sheet pipeline:
        Upload -> Extract Text -> Persist -> Parse Call Sheet Metadata.
        """
        # 1. Save upload
        file_path = save_upload(file, settings.CALL_SHEET_UPLOAD_DIR)

        # 2. Extract text
        raw_text = extract_text(file_path)

        # 3. Persist extracted text
        extracted_path = save_extracted_text(
            text=raw_text,
            destination_dir=settings.CALL_SHEET_EXTRACT_DIR,
            base_filename=file.filename or "call_sheet",
        )

        # 4. Parse call sheet model
        call_sheet_data = parse_call_sheet_to_model(raw_text)

        return CallSheetResponse(
            filename=file.filename or "unknown",
            uploaded_path=file_path,
            extracted_path=extracted_path,
            call_sheet=call_sheet_data,
        )
