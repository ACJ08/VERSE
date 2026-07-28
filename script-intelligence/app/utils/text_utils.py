"""
VERSE Utils - Screenplay Text Pre-processing & Formatting.
"""

import re
from typing import Literal


def clean_screenplay_text(raw: str) -> str:
    """
    Normalize raw screenplay text before scene-splitting or AI analysis.
    
    Applies:
    - Normalization of Windows/Mac line endings to Unix.
    - Stripping trailing whitespace per line.
    - Removal of page break separator lines (e.g. -----, =====, _____).
    - Collapsing consecutive blank lines to a single line.
    """
    if not raw:
        return ""

    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.splitlines()]

    # Remove pure separator lines
    lines = [line for line in lines if not re.fullmatch(r"[-_=]{3,}", line.strip())]

    # Collapse consecutive blank lines
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
    max_chars: int = 3000,
    strategy: Literal["head", "tail", "middle"] = "head",
) -> str:
    """
    Truncate a single scene text string to max_chars characters.
    """
    if len(scene_text) <= max_chars:
        return scene_text

    if strategy == "head":
        return scene_text[:max_chars] + "\n[...truncated...]"
    if strategy == "tail":
        return "[...truncated...]\n" + scene_text[-max_chars:]

    half = max_chars // 2
    return scene_text[:half] + "\n[...truncated...]\n" + scene_text[-half:]
