"""
VERSE Parsers - Screenplay Scene Splitting & Slugline Parser.
"""

import re
from typing import List, Optional
from app.schemas.continuity import SceneMetadata

# Regex matching standard screenplay sluglines at start of line
_SLUGLINE_PATTERN = re.compile(
    r"(?=(?:^\s*(?:\d+[A-Z]?[\.\s]+)?(?:INT\.|EXT\.|INT\./EXT\.|I/E\.|INT/EXT\.|EXT/INT|EST\.)(?:\s+|$)))",
    re.IGNORECASE | re.MULTILINE
)

# Heading breakdown regex for metadata extraction
_HEADING_BREAKDOWN_RE = re.compile(
    r"^(?:\d+[A-Z]?[\.\s]+)?"
    r"(?P<int_ext>INT\.|EXT\.|INT\./EXT\.|I/E\.|INT/EXT\.|EXT/INT|EST\.)\s+"
    r"(?P<location>[^-\n]+?)"
    r"(?:\s+-\s+(?P<sublocation>[^-\n]+?))?"
    r"(?:\s+-\s+(?P<time>DAY|NIGHT|DAWN|DUSK|CONTINUOUS|LATER|MOMENTS LATER|SAME TIME))?\s*$",
    re.IGNORECASE | re.MULTILINE
)


def split_into_scenes(text: str) -> List[str]:
    """
    Split a screenplay text string into individual scenes based on INT/EXT slug lines.
    
    Returns a list of raw scene text blocks.
    """
    if not text or not text.strip():
        return []

    # Perform lookahead split on heading patterns
    raw_scenes = _SLUGLINE_PATTERN.split(text)
    
    # Filter empty blocks and strip whitespace
    scenes = [scene.strip() for scene in raw_scenes if scene and scene.strip()]
    
    # If lookahead split produced only 1 block and no match was found, return the full text as single scene
    return scenes if scenes else [text.strip()]


def parse_scene_metadata(scene_text: str, scene_id: str = "SCENE_001") -> SceneMetadata:
    """
    Parse SceneMetadata from the first line of a scene text block.
    """
    lines = [line.strip() for line in scene_text.strip().splitlines() if line.strip()]
    first_line = lines[0] if lines else ""

    match = _HEADING_BREAKDOWN_RE.match(first_line)
    if match:
        gd = match.groupdict()
        return SceneMetadata(
            scene_id=scene_id,
            heading=first_line,
            interior_exterior=gd["int_ext"].upper() if gd["int_ext"] else None,
            location=gd["location"].strip().upper() if gd["location"] else None,
            sub_location=gd["sublocation"].strip().upper() if gd.get("sublocation") else None,
            time=gd["time"].upper() if gd.get("time") else None,
        )

    return SceneMetadata(
        scene_id=scene_id,
        heading=first_line or None,
    )
