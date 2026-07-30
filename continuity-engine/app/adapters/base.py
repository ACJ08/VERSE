"""Shared plumbing for the producing-team adapters.

Teams 1 and 2 emit the JSON that suits their own pipeline. The engine accepts
arbitrary nested JSON, but "accepted" is not the same as "compared": a fact only
takes part in a continuity check when it lands on the attribute a rule watches
(`wears`, `holds`, `held_in_hand`, `screen_position`, `movement`, `location`,
`lighting`). These adapters are the translation layer that gets it there.

Design rules for everything in this package:

* **Never invent a value.** Empty, null and placeholder values are dropped
  rather than turned into facts — a fact with value ``None`` would be compared
  against real observations and produce phantom issues.
* **Never silently coerce prose into an enum.** Free-text screenplay direction
  ("crosses to the window") and vision enums ("moving") are not the same kind of
  statement. Prose is kept on a `*_description` attribute that no vision output
  ever produces, so it is stored and visible but never compared.
* **Preserve provenance.** The producing team's original field name survives on
  ``Fact.raw_attribute``; adapters only rename the key they hand to the parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.models.schemas import SourceType

# Values that mean "we don't know", in any of the shapes the two pipelines emit.
_PLACEHOLDERS = {"", "-", "--", "n/a", "na", "null", "none specified", "unknown", "unspecified"}


@dataclass
class AdaptedPayload:
    """An engine-ready ingestion payload plus what was learned building it.

    `payload` goes to ``ContinuityEngine.ingest*``. Everything else is reporting
    material for the API response — notes and warnings must not be ingested as
    facts, so they travel alongside the payload rather than inside it.
    """

    payload: dict[str, Any]
    source: SourceType
    scene_ids: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    notes: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    frames_analysed: int = 0

    @property
    def is_empty(self) -> bool:
        container = self.payload.get("scenes") or self.payload.get("observations") or []
        return not container

    def summary(self) -> dict[str, Any]:
        return {
            "source": self.source.value,
            "scenes": len(self.scene_ids),
            "scene_ids": self.scene_ids,
            "entities": self.entities,
            "notes": self.notes,
            "warnings": self.warnings,
            "frames_analysed": self.frames_analysed,
        }


# --------------------------------------------------------------------------- #
# Value hygiene
# --------------------------------------------------------------------------- #


def clean(value: Any) -> Any | None:
    """Return `value` unless it carries no information."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.lower() in _PLACEHOLDERS:
            return None
        return stripped
    if isinstance(value, (list, tuple, set, dict)) and not value:
        return None
    return value


def compact(mapping: dict[str, Any]) -> dict[str, Any]:
    """Drop keys whose value carries no information."""
    out: dict[str, Any] = {}
    for key, value in mapping.items():
        cleaned = clean(value)
        if cleaned is not None:
            out[key] = cleaned
    return out


def sequence_from(scene_id: str, fallback: int) -> int:
    """Screenplay order from a scene id ("SCENE_012" -> 12), else `fallback`."""
    digits = re.findall(r"\d+", scene_id or "")
    return int(digits[-1]) if digits else fallback


def scene_id_for(index: int, prefix: str = "SCENE") -> str:
    return f"{prefix}_{index:03d}"


# --------------------------------------------------------------------------- #
# Screen direction
# --------------------------------------------------------------------------- #

# Canonical screen positions, matching the vocabulary in examples/ and the
# `screen_direction_mismatch` rule.
FRAME_LEFT = "frame left"
FRAME_RIGHT = "frame right"
FRAME_CENTRE = "frame centre"

_DIRECTION_WORDS: list[tuple[str, tuple[str, ...]]] = [
    (FRAME_CENTRE, ("centre", "center", "middle", "mid-frame")),
    (FRAME_LEFT, ("left",)),
    (FRAME_RIGHT, ("right",)),
]


def screen_direction(text: Any) -> str | None:
    """Canonical screen position from vision enums or screenplay prose.

    Vision emits "left" / "center" / "right"; the script says things like
    "standing frame left" or "by the door". Only an unambiguous single
    direction is returned — prose naming two sides ("moves left to right")
    describes a move, not a position, and yields None.
    """
    cleaned = clean(text)
    if not isinstance(cleaned, str):
        return None
    lowered = cleaned.lower()
    found = {
        canonical
        for canonical, needles in _DIRECTION_WORDS
        if any(needle in lowered for needle in needles)
    }
    if len(found) != 1:
        return None
    return found.pop()


# --------------------------------------------------------------------------- #
# Movement state
# --------------------------------------------------------------------------- #

MOVING = "moving"
STATIONARY = "stationary"

# Checked before the moving verbs so "stands still" is not read as "stands up".
_STATIONARY_PHRASES = (
    "stationary", "motionless", "stands still", "standing still", "remains still",
    "does not move", "doesn't move", "no movement", "remains seated", "stays seated",
    "seated", "sitting", "sits", "frozen", "unmoving", "static", "waits", "still",
)
_MOVING_PHRASES = (
    "moving", "moves", "crosses", "walks", "walking", "runs", "running", "enters",
    "exits", "leaves", "steps", "stepping", "paces", "approaches", "rushes",
    "hurries", "climbs", "descends", "jumps", "turns", "rises", "stands up",
    "gets up", "strides", "wanders", "circles", "follows", "backs away",
)


def movement_state(text: Any) -> str | None:
    """Coarse movement state from a vision enum or screenplay prose.

    The vision pipeline already emits "moving" / "stationary"; screenplay
    direction is prose. Both collapse onto the same two-value vocabulary so the
    `movement_mismatch` rule has something comparable to work with. Prose that
    implies neither returns None and is kept as prose by the caller.
    """
    cleaned = clean(text)
    if not isinstance(cleaned, str):
        return None
    lowered = cleaned.lower()
    if any(phrase in lowered for phrase in _STATIONARY_PHRASES):
        return STATIONARY
    if any(phrase in lowered for phrase in _MOVING_PHRASES):
        return MOVING
    return None


# --------------------------------------------------------------------------- #
# Hands
# --------------------------------------------------------------------------- #

_HANDS = {"left", "right", "both", "none"}


def hand_value(text: Any) -> str | None:
    """Normalise a hand reference to left / right / both / none.

    Both pipelines already use this vocabulary (team 1 validates it on
    `Prop.hand_usage`, team 2 emits it from wrist association), so this only
    has to survive casing and phrasing like "left hand".
    """
    cleaned = clean(text)
    if not isinstance(cleaned, str):
        return None
    lowered = cleaned.lower()
    if lowered in _HANDS:
        return lowered
    if "both" in lowered:
        return "both"
    left, right = "left" in lowered, "right" in lowered
    if left and right:
        return "both"
    if left:
        return "left"
    if right:
        return "right"
    if "no hand" in lowered or lowered in {"neither", "not held"}:
        return "none"
    return None


# --------------------------------------------------------------------------- #
# Entity aliasing
# --------------------------------------------------------------------------- #


def build_alias_lookup(*tables: Any) -> dict[str, str]:
    """Flatten alias declarations into a lowercased ``alias -> canonical`` map.

    Accepts either direction so callers can pass whichever they have:
      * ``{"PERSON_1": "Sarah"}``            — alias to canonical
      * ``{"Sarah": ["PERSON_1", "PERSON_2"]}`` — canonical to aliases
    """
    lookup: dict[str, str] = {}
    for table in tables:
        if not isinstance(table, dict):
            continue
        for key, value in table.items():
            if isinstance(value, str):
                lookup[str(key).strip().lower()] = value.strip()
            elif isinstance(value, (list, tuple)):
                for alias in value:
                    lookup[str(alias).strip().lower()] = str(key).strip()
    return lookup


def apply_alias(name: str, lookup: dict[str, str]) -> str:
    return lookup.get(name.strip().lower(), name.strip())
