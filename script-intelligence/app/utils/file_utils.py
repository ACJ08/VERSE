"""
VERSE Utils - Security Hardened File I/O & Validation.
"""

import os
import re
import shutil
from typing import Optional
from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import SecurityError, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)


def sanitize_filename(filename: Optional[str]) -> str:
    """
    Sanitize an uploaded filename to prevent Path Traversal attacks.
    Removes path components and directory traversal sequences.
    """
    if not filename:
        return "unnamed_upload"
    
    # Strip directory components
    base_name = os.path.basename(filename)
    
    # Replace non-alphanumeric chars (except dot, dash, underscore) with underscore
    clean_name = re.sub(r"[^\w\.-]", "_", base_name)
    
    # Remove leading dots to prevent hidden files
    clean_name = clean_name.lstrip(".")
    
    return clean_name or "upload.file"


def validate_upload_file(file: UploadFile) -> str:
    """
    Validate extension, MIME type, and size of an uploaded file.
    
    Returns sanitized filename if valid.
    Raises SecurityError / ValidationError on check failure.
    """
    sanitized_name = sanitize_filename(file.filename)
    ext = os.path.splitext(sanitized_name)[-1].lower()

    # 1. Extension check
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise ValidationError(
            message=f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(settings.ALLOWED_EXTENSIONS))}"
        )

    # 2. Content Type / MIME check
    if file.content_type and file.content_type not in settings.ALLOWED_MIME_TYPES:
        logger.warning("Upload MIME type warning: '%s' for file '%s'", file.content_type, sanitized_name)

    # 3. File size check (if content size available in headers or by checking stream)
    file.file.seek(0, os.SEEK_END)
    size_bytes = file.file.tell()
    file.file.seek(0)

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise SecurityError(
            message=f"File size ({size_bytes / (1024*1024):.2f}MB) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    return sanitized_name


def save_upload(file: UploadFile, destination_dir: str) -> str:
    """
    Safely persist an UploadFile to disk under destination_dir.
    """
    sanitized_name = validate_upload_file(file)
    os.makedirs(destination_dir, exist_ok=True)
    dest_path = os.path.join(destination_dir, sanitized_name)

    try:
        file.file.seek(0)
        with open(dest_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
    except OSError as exc:
        logger.exception("Failed to save upload '%s'.", sanitized_name)
        raise SecurityError(message=f"Could not save file to disk: {exc}") from exc

    logger.info("Saved upload → %s", dest_path)
    return dest_path


def save_extracted_text(text: str, destination_dir: str, base_filename: str) -> str:
    """
    Save extracted text content to a .txt file inside destination_dir.
    """
    clean_base = sanitize_filename(base_filename)
    os.makedirs(destination_dir, exist_ok=True)
    txt_name = f"{clean_base}.txt"
    txt_path = os.path.join(destination_dir, txt_name)

    try:
        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write(text)
    except OSError as exc:
        logger.exception("Failed to save extracted text for '%s'.", base_filename)
        raise SecurityError(message=f"Could not save extracted text file: {exc}") from exc

    logger.info("Saved extracted text → %s", txt_path)
    return txt_path
