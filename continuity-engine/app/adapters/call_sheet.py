"""Team 1 (Call Sheet parser) -> engine call-sheet payload.

The script service also parses production call sheets:

    {"filename": "day12.pdf",
     "call_sheet": {"date": "2026-03-04", "production": "...", "director": "...",
                    "location": "STAGE 4 / COFFEE SHOP", "scenes": ["12", "13"],
                    "cast": ["SARAH - 07:00"], "crew": [...],
                    "shooting_time": "06:30"}}

A call sheet is a statement of intent about a shooting day — which scenes, where,
with whom — so it ingests as `SourceType.CALL_SHEET`, ranking below the script
but above footage. Its main contribution is location: when the call sheet and
the screenplay disagree about where a scene happens, that is worth flagging
before the crew travels.
"""

from __future__ import annotations

import re
from typing import Any

from app.adapters.base import AdaptedPayload, clean, compact, scene_id_for, sequence_from
from app.models.schemas import SourceType


def looks_like_call_sheet(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if isinstance(payload.get("call_sheet"), dict):
        return True
    keys = {k.lower() for k in payload}
    return "shooting_time" in keys or {"cast", "crew", "scenes"} <= keys


def adapt_call_sheet(payload: Any, *, scene_prefix: str = "SCENE") -> AdaptedPayload:
    """Reshape a parsed call sheet into per-scene engine facts."""
    sheet = payload.get("call_sheet") if isinstance(payload.get("call_sheet"), dict) else payload
    if not isinstance(sheet, dict):
        return AdaptedPayload(payload={"scenes": []}, source=SourceType.CALL_SHEET)

    location = clean(sheet.get("location"))
    shoot_date = clean(sheet.get("date"))
    cast = [name for name in (_cast_name(entry) for entry in sheet.get("cast") or []) if name]
    warnings: list[str] = []

    scene_ids = [sid for sid in (_scene_id(raw, scene_prefix) for raw in sheet.get("scenes") or []) if sid]
    if not scene_ids:
        warnings.append("Call sheet listed no scene numbers; nothing could be attached to a scene.")

    scenes: list[dict[str, Any]] = []
    for index, scene_id in enumerate(scene_ids, start=1):
        scene = compact(
            {
                "scene_id": scene_id,
                "sequence": sequence_from(scene_id, index),
                "location": location,
                "shoot_date": shoot_date,
                "call_time": clean(sheet.get("shooting_time")),
            }
        )
        # The cast list says who is scheduled, which is the call sheet's
        # equivalent of "these characters appear in this scene".
        if cast:
            scene["characters"] = [{"name": name, "type": "character", "scheduled": True} for name in cast]
        scenes.append(scene)

    return AdaptedPayload(
        payload={"source": SourceType.CALL_SHEET.value, "scenes": scenes},
        source=SourceType.CALL_SHEET,
        scene_ids=scene_ids,
        entities=sorted({f"character:{name}" for name in cast}),
        warnings=warnings,
    )


def _scene_id(raw: Any, prefix: str) -> str | None:
    """Call sheets write scene numbers as "12", "12A" or "SC 12"."""
    text = clean(raw)
    if not isinstance(text, str):
        if isinstance(raw, int):
            return scene_id_for(raw, prefix)
        return None
    if re.fullmatch(r"(?i)scene[_ ]?\d+[a-z]?", text.strip()):
        digits = re.findall(r"\d+", text)
        return scene_id_for(int(digits[0]), prefix)
    digits = re.findall(r"\d+", text)
    return scene_id_for(int(digits[0]), prefix) if digits else None


def _cast_name(entry: Any) -> str | None:
    """Cast lines carry call times: "SARAH - 07:00" -> "SARAH"."""
    text = clean(entry)
    if not isinstance(text, str):
        return None
    name = re.split(r"\s+[-–—]\s+|\s{2,}|,", text, maxsplit=1)[0]
    name = re.sub(r"\b\d{1,2}[:.]\d{2}\s*(am|pm)?\b", "", name, flags=re.IGNORECASE).strip()
    return name or None
