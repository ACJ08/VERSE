"""
VERSE Parsers - Production Call Sheet Extractor & Structural Parser.
"""

import re
from typing import Dict, Any, List
from app.schemas.call_sheet import CallSheetData


def parse_call_sheet(text: str) -> Dict[str, Any]:
    """
    Parse unstructured call sheet text into structured dictionary format.
    
    Extracts date, production title, director, location, scenes, cast, crew, and shooting time.
    """
    data = {
        "date": "",
        "production": "",
        "director": "",
        "location": "",
        "scenes": [],
        "cast": [],
        "crew": [],
        "shooting_time": ""
    }

    if not text or not text.strip():
        return data

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 1. Key-Value metadata extraction
    for line in lines:
        lower = line.lower()

        # Date
        if "date:" in lower or "date |" in lower or lower.startswith("date"):
            parts = re.split(r"[:|]", line)
            if len(parts) > 1:
                data["date"] = parts[-1].strip()

        # Production
        if "production:" in lower or "production |" in lower or "title:" in lower:
            parts = re.split(r"[:|]", line)
            if len(parts) > 1:
                data["production"] = parts[-1].strip()

        # Director
        if "director:" in lower or "director |" in lower:
            parts = re.split(r"[:|]", line)
            if len(parts) > 1:
                data["director"] = parts[-1].strip()

        # Location
        if "location:" in lower or "location |" in lower or "set:" in lower:
            parts = re.split(r"[:|]", line)
            if len(parts) > 1:
                data["location"] = parts[-1].strip()

        # Shooting time / Call time
        if "call" in lower or "shoot call" in lower or "crew call" in lower:
            time_match = re.search(r"\b\d{1,2}:\d{2}(?:\s*[AP]\.?M\.?)?\b", line, re.IGNORECASE)
            if time_match:
                data["shooting_time"] = time_match.group(0).strip()

    # 2. Scene schedule extraction
    scenes_set: List[str] = []
    for line in lines:
        # Match table rows starting with scene numbers, e.g. "1A | INT. KITCHEN | ..." or "101 - ..."
        scene_match = re.match(r"^(\d+[A-Z]?)\s*[:|-]", line)
        if scene_match:
            scene_num = scene_match.group(1).strip()
            if scene_num not in scenes_set:
                scenes_set.append(scene_num)
        elif re.match(r"^\d+[A-Z]?\s*\|", line):
            scene_num = line.split("|")[0].strip()
            if scene_num not in scenes_set:
                scenes_set.append(scene_num)

    data["scenes"] = scenes_set

    # 3. CAST section extraction
    cast_lines: List[str] = []
    in_cast_section = False

    for line in lines:
        line_upper = line.upper()

        if "CAST" in line_upper and ("LIST" in line_upper or "TALENT" in line_upper or line_upper == "CAST"):
            in_cast_section = True
            continue

        if "CREW" in line_upper and ("LIST" in line_upper or "DEPARTMENT" in line_upper or line_upper == "CREW"):
            in_cast_section = False
            continue

        if in_cast_section:
            if line_upper.startswith("SCENE") or line_upper.startswith("LOCATION"):
                in_cast_section = False
            else:
                cast_lines.append(line)

    data["cast"] = cast_lines

    # 4. CREW section extraction
    crew_lines: List[str] = []
    in_crew_section = False

    for line in lines:
        line_upper = line.upper()

        if "CREW" in line_upper and ("LIST" in line_upper or "DEPARTMENT" in line_upper or line_upper == "CREW"):
            in_crew_section = True
            continue

        if in_crew_section:
            if line_upper.startswith("END") or line_upper.startswith("NOTES"):
                in_crew_section = False
            else:
                crew_lines.append(line)

    data["crew"] = crew_lines

    return data


def parse_call_sheet_to_model(text: str) -> CallSheetData:
    """
    Parse call sheet text and return a validated Pydantic model.
    """
    parsed_dict = parse_call_sheet(text)
    return CallSheetData.model_validate(parsed_dict)
