"""
VERSE – Continuity Script Intelligence
app/parser.py (Backwards Compatibility Layer)

Re-exports document extraction functions from app.parsers.document_parser.
"""

from app.parsers.document_parser import (
    extract_text,
    extract_pdf,
    extract_docx,
    extract_txt,
)

__all__ = [
    "extract_text",
    "extract_pdf",
    "extract_docx",
    "extract_txt",
]