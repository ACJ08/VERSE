"""MOCK stand-in for team 1 (Script Intelligence & Granite).

Regex, not an LLM. It exists so the continuity engine has realistic script JSON
to consume before team 1's pipeline lands. Delete this file the moment their
real extractor produces the shape documented in docs/INTEGRATION.md.

The output contract is what matters here, not how it was produced.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_SCENE = re.compile(r"^SCENE\s+(\d+)\s*-\s*(.+)$", re.IGNORECASE)
_LIGHTING = re.compile(r"^LIGHTING:\s*(.+)$", re.IGNORECASE)
# "SARAH holds glass in left hand, wears blue blazer, at frame left."
_CHARACTER = re.compile(r"^([A-Z][A-Z ]{1,20})\s+(.+)$")
_HOLDS = re.compile(r"holds\s+(?:the\s+)?([a-z ]+?)(?:\s+in\s+(left|right)\s+hand)?(?:,|$|\.)")
_WEARS = re.compile(r"wears\s+(?:a\s+|an\s+|the\s+)?([a-z ]+?)(?:,|$|\.)")
_POSITION = re.compile(r"at\s+(frame\s+(?:left|right|centre|center))")


def extract(screenplay: str) -> dict[str, Any]:
    """Parse screenplay text into the script JSON contract."""
    scenes: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    narrative: list[str] = []

    for raw in screenplay.splitlines():
        line = raw.strip()
        if not line:
            continue

        scene_match = _SCENE.match(line)
        if scene_match:
            if current is not None:
                current["action"] = " ".join(narrative)
                scenes.append(current)
            number = int(scene_match.group(1))
            heading = scene_match.group(2).strip()
            current = {
                "scene_id": f"SCENE_{number:03d}",
                "sequence": number,
                "location": _location_from(heading),
                "heading": heading,
                "characters": [],
                "props": [],
            }
            narrative = []
            continue

        if current is None:
            continue  # title block

        lighting_match = _LIGHTING.match(line)
        if lighting_match:
            current["lighting"] = lighting_match.group(1).strip().lower()
            continue

        character_match = _CHARACTER.match(line)
        if character_match and " " in line:
            entry = _character_entry(character_match.group(1), character_match.group(2))
            if entry is not None:
                current["characters"].append(entry)
                if entry.get("holds"):
                    current["props"].append(
                        {"name": entry["holds"], "type": "prop", "location": "held"}
                    )
                continue

        narrative.append(line)

    if current is not None:
        current["action"] = " ".join(narrative)
        scenes.append(current)

    return {"project_id": "VERSE_DEMO", "source": "script", "scenes": scenes}


def _character_entry(name: str, rest: str) -> dict[str, Any] | None:
    lowered = rest.lower()
    entry: dict[str, Any] = {"name": name.strip().title(), "type": "character"}

    holds = _HOLDS.search(lowered)
    if holds:
        entry["holds"] = holds.group(1).strip()
        if holds.group(2):
            entry["held_in_hand"] = holds.group(2)

    wears = _WEARS.search(lowered)
    if wears:
        entry["wears"] = wears.group(1).strip()

    position = _POSITION.search(lowered)
    if position:
        entry["screen_position"] = position.group(1).strip()

    # A line with a name but no recognised attributes is prose, not a character row.
    return entry if len(entry) > 2 else None


def _location_from(heading: str) -> str:
    body = re.sub(r"^(INT\.|EXT\.)\s*", "", heading, flags=re.IGNORECASE)
    return body.split("-")[0].strip().lower()


def extract_file(path: str | Path) -> dict[str, Any]:
    return extract(Path(path).read_text(encoding="utf-8"))
