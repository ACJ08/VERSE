"""
VERSE – Continuity Script Intelligence
app/utils.py (Backwards Compatibility Layer)

Re-exports utility helpers from app.utils.
"""

from app.utils.file_utils import save_upload, save_extracted_text
from app.utils.text_utils import clean_screenplay_text, truncate_scene_text
from app.parsers.document_parser import extract_text

ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx", ".txt"}

__all__ = [
    "save_upload",
    "save_extracted_text",
    "clean_screenplay_text",
    "truncate_scene_text",
    "extract_text",
    "ALLOWED_EXTENSIONS",
]
