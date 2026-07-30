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


def extract_action_prose(scene_text: str, max_chars: int = 1200) -> str:
    """
    Extract the action/description prose of a scene, dropping the slug line,
    character cues, parentheticals and dialogue.

    Continuity reasoning downstream reads this prose to spot scripted state
    changes ("SARAH removes her blazer") and narrative events that can explain a
    discrepancy ("the crowd panics"). Dialogue rarely carries either and dilutes
    the signal, so only description lines are kept.
    """
    if not scene_text or not scene_text.strip():
        return ""

    lines = [line.strip() for line in scene_text.strip().splitlines()]
    action_lines: list[str] = []
    in_dialogue = False

    for index, line in enumerate(lines):
        if not line:
            in_dialogue = False
            continue
        if index == 0 and re.match(r"^(?:\d+[A-Z]?[\.\s]+)?(?:INT|EXT|I/E|EST)[\./]", line, re.IGNORECASE):
            continue  # slug line — already captured in SceneMetadata
        if re.fullmatch(r"\(.*\)", line):
            continue  # parenthetical
        if re.fullmatch(r"(?:CUT TO|FADE (?:IN|OUT|TO)|DISSOLVE TO|SMASH CUT)[:.]?", line, re.IGNORECASE):
            continue  # transition
        # A short all-caps line is a character cue; the lines under it are that
        # character's dialogue, until the next blank line.
        if line.isupper() and len(line) < 40 and not line.endswith("."):
            in_dialogue = True
            continue
        if in_dialogue:
            continue
        action_lines.append(line)

    prose = " ".join(action_lines)
    prose = re.sub(r"\s{2,}", " ", prose).strip()
    return prose[:max_chars]


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
