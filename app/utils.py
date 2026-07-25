"""
VERSE – Continuity Script Intelligence
app/utils.py

Shared utility helpers used across the API layer.

Responsibilities
----------------
* Save an incoming FastAPI ``UploadFile`` to disk (with allowed-extension
  validation) and return the saved path.
* Provide a thin wrapper around ``app.parser.extract_text`` so that both
  ``app.api`` and ``app.main`` can call a single, well-typed surface.
* Expose helper functions for cleaning raw screenplay text before it is
  passed to the scene-splitter or the Granite integration.

All I/O errors are surfaced as ``HTTPException`` so callers do not need
to add their own try/except for expected failure modes.
"""

import os
import re
import shutil
import logging
from typing import Literal

from fastapi import HTTPException, UploadFile, status

from app.parser import extract_text as _extract_text_from_path

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed upload extensions
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx", ".txt"}


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def save_upload(
    file: UploadFile,
    destination_dir: str,
) -> str:
    """
    Persist an ``UploadFile`` to *destination_dir* on disk.

    Parameters
    ----------
    file:
        The multipart upload received by a FastAPI route.
    destination_dir:
        The directory where the file should be written.  Created
        automatically if it does not exist.

    Returns
    -------
    str
        Absolute path to the saved file.

    Raises
    ------
    HTTPException(415)
        When the file extension is not in ``ALLOWED_EXTENSIONS``.
    HTTPException(500)
        When writing to disk fails for any reason.
    """
    # --- validate extension ---------------------------------------------------
    filename: str = file.filename or "upload"
    ext: str = os.path.splitext(filename)[-1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    # --- persist to disk -----------------------------------------------------
    os.makedirs(destination_dir, exist_ok=True)
    dest_path: str = os.path.join(destination_dir, filename)

    try:
        file.file.seek(0)  # ensure we read from the beginning
        with open(dest_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
    except OSError as exc:
        logger.exception("Failed to save upload '%s'.", filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {exc}",
        ) from exc

    logger.info("Saved upload → %s", dest_path)
    return dest_path


def save_extracted_text(
    text: str,
    destination_dir: str,
    base_filename: str,
) -> str:
    """
    Write *text* to a ``.txt`` file inside *destination_dir*.

    Parameters
    ----------
    text:
        The extracted plain-text content.
    destination_dir:
        Directory that will hold the extracted file.
    base_filename:
        Original filename (e.g. ``screenplay.pdf``).  The ``.txt``
        suffix is appended automatically.

    Returns
    -------
    str
        Path to the written text file.
    """
    os.makedirs(destination_dir, exist_ok=True)
    txt_name: str = base_filename + ".txt"
    txt_path: str = os.path.join(destination_dir, txt_name)

    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write(text)

    logger.info("Saved extracted text → %s", txt_path)
    return txt_path


# ---------------------------------------------------------------------------
# Text extraction wrapper
# ---------------------------------------------------------------------------

def extract_text(file_path: str) -> str:
    """
    Extract plain text from a file on disk.

    Delegates to ``app.parser.extract_text`` and converts ``ValueError``
    (unsupported format) into an ``HTTPException(415)``.

    Parameters
    ----------
    file_path:
        Absolute or relative path to the file.

    Returns
    -------
    str
        Raw extracted text content.

    Raises
    ------
    HTTPException(415)
        When the file format is not supported by the parser.
    HTTPException(500)
        When extraction fails for any unexpected reason.
    """
    try:
        return _extract_text_from_path(file_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Text extraction failed for '%s'.", file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text extraction error: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Text pre-processing helpers
# ---------------------------------------------------------------------------

def clean_screenplay_text(raw: str) -> str:
    """
    Normalize raw screenplay text before scene-splitting or AI analysis.

    Transformations applied
    -----------------------
    * Collapse runs of blank lines to a single blank line.
    * Strip trailing whitespace from every line.
    * Remove page-break artifacts (lines of only dashes or underscores).
    * Normalize Windows-style line endings to Unix.

    Parameters
    ----------
    raw:
        The raw text as returned by ``extract_text``.

    Returns
    -------
    str
        Cleaned, normalized text.
    """
    # Normalize line endings
    text: str = raw.replace("\r\n", "\n").replace("\r", "\n")

    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.splitlines()]

    # Remove pure separator lines (----, ====, ____)
    lines = [
        line for line in lines
        if not re.fullmatch(r"[-_=]{3,}", line.strip())
    ]

    # Collapse consecutive blank lines → single blank line
    cleaned_lines: list[str] = []
    prev_blank = False
    for line in lines:
        is_blank = line.strip() == ""
        if is_blank and prev_blank:
            continue
        cleaned_lines.append(line)
        prev_blank = is_blank

    return "\n".join(cleaned_lines).strip()


def truncate_scene_text(
    scene_text: str,
    max_chars: int = 3_000,
    strategy: Literal["head", "tail", "middle"] = "head",
) -> str:
    """
    Truncate a single scene to *max_chars* characters.

    Used to keep Granite prompts within token budget limits.

    Parameters
    ----------
    scene_text:
        Full text of one scene block.
    max_chars:
        Maximum number of characters to keep (default 3 000).
    strategy:
        Which portion of the text to keep:
        ``"head"`` – first N chars (default, preserves the scene heading),
        ``"tail"`` – last N chars,
        ``"middle"`` – centre slice.

    Returns
    -------
    str
        Possibly-truncated scene text, with an ellipsis appended when
        text was actually cut.
    """
    if len(scene_text) <= max_chars:
        return scene_text

    if strategy == "head":
        return scene_text[:max_chars] + "\n[...truncated...]"
    if strategy == "tail":
        return "[...truncated...]\n" + scene_text[-max_chars:]

    # middle
    half = max_chars // 2
    start = scene_text[:half]
    end = scene_text[-half:]
    return start + "\n[...truncated...]\n" + end
