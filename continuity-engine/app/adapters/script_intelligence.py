"""Team 1 (Script Intelligence) -> engine script payload.

The script service returns `AnalyseScriptResponse`:

    {"filename": "...", "scene_count": 3,
     "scenes": [{"metadata": {"scene_id": "SCENE_001", "heading": "INT. ...",
                              "location": "COFFEE SHOP", "time": "DAY"},
                 "characters": [{"name": "SARAH", "costume": "blue blazer",
                                 "position": "by the window", "movement": "...",
                                 "emotional_state": "tense"}],
                 "props": [{"name": "glass", "hand_usage": "left",
                            "state": "full", "owner": "SARAH"}],
                 "lighting": {"description": "...", "time_of_day": "DAY"},
                 "continuity_notes": [...], "confidence_score": 1.0}]}

The engine wants what `examples/script_scenes.json` shows: flat scenes carrying
`scene_id` / `sequence` / `location` / `action` with entity attributes on the
entities themselves. This module performs that reshape, and in particular:

* lifts `metadata.scene_id` to the top of the scene, which is the join key with
  team 2's footage,
* re-homes `props[].owner` + `hand_usage` onto the owning character as
  `holds` / `held_in_hand`, which is what the props rules compare,
* keeps `continuity_notes` out of the fact stream — they are the script model's
  own opinions, not observations of the production.
"""

from __future__ import annotations

from typing import Any

from app.adapters.base import (
    AdaptedPayload,
    clean,
    compact,
    hand_value,
    movement_state,
    scene_id_for,
    screen_direction,
    sequence_from,
)
from app.models.schemas import SourceType

# Longest action text handed to the engine. The assumption engine mines this
# prose for explicit changes and narrative triggers; whole scenes of dialogue
# add tokens without adding signal.
_MAX_ACTION_CHARS = 2000


def looks_like_script_intelligence(payload: Any) -> bool:
    """True when this payload is team 1's shape rather than the engine's own."""
    scenes = _scene_list(payload)
    if not scenes:
        return False
    return any(isinstance(scene.get("metadata"), dict) for scene in scenes if isinstance(scene, dict))


def adapt_script_intelligence(
    payload: Any,
    *,
    scene_prefix: str = "SCENE",
) -> AdaptedPayload:
    """Reshape a script-intelligence response into an engine script payload."""
    scenes_in = _scene_list(payload)
    scenes_out: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    warnings: list[str] = []
    entities: list[str] = []

    for index, scene in enumerate(scenes_in, start=1):
        if not isinstance(scene, dict):
            warnings.append(f"Skipped scene {index}: expected an object, got {type(scene).__name__}.")
            continue

        meta = scene.get("metadata") if isinstance(scene.get("metadata"), dict) else {}
        scene_id = (
            clean(meta.get("scene_id"))
            or clean(scene.get("scene_id"))
            or scene_id_for(index, scene_prefix)
        )
        adapted: dict[str, Any] = {
            "scene_id": scene_id,
            "sequence": scene.get("sequence") or sequence_from(scene_id, index),
        }

        confidence = _confidence(scene.get("confidence_score"))
        if confidence is not None:
            adapted["confidence"] = confidence

        adapted.update(_scene_attributes(scene, meta))

        characters, character_warnings = _characters(scene.get("characters"), scene_id)
        props, prop_holdings, prop_warnings = _props(scene.get("props"), scene_id)
        warnings.extend(character_warnings)
        warnings.extend(prop_warnings)

        # A prop with an owner is also a statement about the character holding
        # it. Emitted as extra character entries rather than merged so a
        # character carrying two props produces two `holds` facts instead of one
        # overwriting the other.
        characters.extend(prop_holdings)

        if characters:
            adapted["characters"] = characters
        if props:
            adapted["props"] = props

        entities.extend(f"character:{c['name']}" for c in characters if "name" in c)
        entities.extend(f"prop:{p['name']}" for p in props if "name" in p)

        for note in _notes(scene.get("continuity_notes"), scene_id):
            notes.append(note)

        if len(adapted) <= 2:
            warnings.append(
                f"{scene_id}: no usable continuity data (no location, action, characters or props)."
            )
        scenes_out.append(adapted)

    return AdaptedPayload(
        payload={"source": SourceType.SCRIPT.value, "scenes": scenes_out},
        source=SourceType.SCRIPT,
        scene_ids=[s["scene_id"] for s in scenes_out],
        entities=sorted(set(entities)),
        notes=notes,
        warnings=warnings,
    )


# --------------------------------------------------------------------------- #
# Scene level
# --------------------------------------------------------------------------- #


def _scene_list(payload: Any) -> list[Any]:
    """Accept a full response, a bare scenes list, or a single scene."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    scenes = payload.get("scenes")
    if isinstance(scenes, list):
        return scenes
    if isinstance(payload.get("metadata"), dict):
        return [payload]
    return []


def _scene_attributes(scene: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    """Scene-level facts: location, time of day, lighting, action prose."""
    location = clean(meta.get("location")) or clean(scene.get("location"))
    lighting = scene.get("lighting") if isinstance(scene.get("lighting"), dict) else {}

    # `time` is reserved: the parser reads it as a footage timestamp, so the
    # canonical attribute name has to be `time_of_day`.
    time_of_day = clean(meta.get("time")) or clean(lighting.get("time_of_day"))

    return compact(
        {
            "location": location,
            "sub_location": meta.get("sub_location"),
            "int_ext": meta.get("interior_exterior"),
            "slugline": meta.get("heading"),
            "time_of_day": time_of_day,
            "lighting": clean(lighting.get("description")) or clean(lighting.get("source")),
            "lighting_mood": lighting.get("mood"),
            "lighting_source": lighting.get("source") if lighting.get("description") else None,
            "action": _action_text(scene),
        }
    )


def _action_text(scene: dict[str, Any]) -> str | None:
    """The prose the assumption engine reads.

    `raw_scene_text` is excluded from the script service's JSON by default, so
    `action` is the field to rely on; both are accepted here.
    """
    for key in ("action", "raw_scene_text", "scene_text", "description"):
        text = clean(scene.get(key))
        if isinstance(text, str):
            return text[:_MAX_ACTION_CHARS]
    return None


def _confidence(raw: Any) -> float | None:
    if not isinstance(raw, (int, float)) or isinstance(raw, bool):
        return None
    value = max(0.0, min(1.0, float(raw)))
    return value if value < 1.0 else None


# --------------------------------------------------------------------------- #
# Entities
# --------------------------------------------------------------------------- #


def _characters(raw: Any, scene_id: str) -> tuple[list[dict[str, Any]], list[str]]:
    out: list[dict[str, Any]] = []
    warnings: list[str] = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        name = clean(entry.get("name"))
        if not isinstance(name, str):
            warnings.append(f"{scene_id}: dropped a character with no name.")
            continue

        position = clean(entry.get("position"))
        movement = clean(entry.get("movement"))
        character = compact(
            {
                "name": name,
                "type": "character",
                "wears": entry.get("costume"),
                # Only a stated screen side is comparable to vision output;
                # everything else stays prose on a non-compared attribute.
                "screen_position": screen_direction(position),
                "blocking_description": position,
                "movement": movement_state(movement),
                "movement_description": movement,
                "emotional_state": entry.get("emotional_state"),
            }
        )
        out.append(character)
    return out, warnings


def _props(raw: Any, scene_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Props plus the character-side `holds` statements their owners imply."""
    props: list[dict[str, Any]] = []
    holdings: list[dict[str, Any]] = []
    warnings: list[str] = []

    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        name = clean(entry.get("name"))
        if not isinstance(name, str):
            warnings.append(f"{scene_id}: dropped a prop with no name.")
            continue

        hand = hand_value(entry.get("hand_usage"))
        owner = clean(entry.get("owner"))
        props.append(
            compact(
                {
                    "name": name,
                    "type": "prop",
                    "held_in_hand": hand,
                    "prop_state": entry.get("state"),
                    "owner": owner,
                }
            )
        )

        if isinstance(owner, str):
            holdings.append(
                compact(
                    {
                        "name": owner,
                        "type": "character",
                        "holds": name,
                        "held_in_hand": hand,
                    }
                )
            )

    return props, holdings, warnings


def _notes(raw: Any, scene_id: str) -> list[dict[str, Any]]:
    """Team 1's continuity notes — reported to the UI, never ingested as facts."""
    notes: list[dict[str, Any]] = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        text = clean(entry.get("note"))
        if not isinstance(text, str):
            continue
        notes.append(
            {
                "scene_id": scene_id,
                "note": text,
                "severity": (clean(entry.get("severity")) or "LOW"),
                "category": (clean(entry.get("category")) or "OTHER"),
                "affected_characters": entry.get("affected_characters") or [],
            }
        )
    return notes
