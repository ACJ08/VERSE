"""Team 2 (Vision) -> engine footage payload.

The vision pipeline samples a clip at ~2 fps and emits one observation per
frame:

    {"scene_id": "SCENE_001",
     "observations": [{"frame_id": 3, "timestamp": "00:00:01.440",
                       "characters": [{"name": "PERSON_1", "costume": "black",
                                       "position": "left", "movement": "stationary"}],
                       "props": [{"name": "wine glass", "hand_usage": "left"}],
                       "detections": [{"type": "character", "name": "PERSON_1",
                                       "confidence": 0.509}]}]}

Handing that to the engine frame by frame would be wrong twice over. It would
emit ~40 competing facts per attribute per scene, and per-frame detector noise
(a torso colour that reads "black" in one frame and "pink" in the next) would
surface as continuity issues that no human would call errors.

So this adapter aggregates each scene to one statement per entity attribute:

* the **modal value** across frames wins,
* confidence is the mean detector confidence for the frames backing that value,
  scaled by how large a share of the reporting frames agreed. A value seen in
  every frame keeps its detector confidence; a value seen in half of them is
  halved, and typically falls under `min_observation_confidence` — which is
  exactly the "please send honest values" contract in docs/INTEGRATION.md,
* the timestamp of the first frame backing the value is kept as the source
  reference, so the UI still cites a real moment in the clip.

Vision has no idea who "PERSON_1" is. `entity_aliases` is the join with the
script's names; without it, footage facts land on their own entities and simply
never conflict with anything.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from app.adapters.base import (
    AdaptedPayload,
    apply_alias,
    build_alias_lookup,
    clean,
    hand_value,
    movement_state,
    screen_direction,
    sequence_from,
)
from app.models.schemas import SourceType

# Confidence multiplier for a prop-to-character attribution the vision pipeline
# did not make itself (see `_infer_owner`). Kept well below 1.0 and emitted as
# `ai_inference` so the trust model treats it as the weakest kind of evidence.
_INFERRED_OWNER_FACTOR = 0.8

_DEFAULT_SCENE_ID = "SCENE_001"


def looks_like_vision(payload: Any) -> bool:
    """True when this payload is team 2's per-frame shape."""
    frames = _frame_list(payload)
    if not frames:
        return False
    return any(
        isinstance(frame, dict) and ("frame_id" in frame or "characters" in frame or "props" in frame)
        for frame in frames
    )


def adapt_vision(
    payload: Any,
    *,
    scene_id: str | None = None,
    sequence: int | None = None,
    entity_aliases: dict[str, Any] | None = None,
    infer_prop_owner: bool = True,
) -> AdaptedPayload:
    """Aggregate a vision scene document into one engine footage observation."""
    frames = _frame_list(payload)
    resolved_scene_id = (
        clean(payload.get("scene_id")) if isinstance(payload, dict) else None
    ) or clean(scene_id) or _DEFAULT_SCENE_ID
    resolved_sequence = sequence or _sequence(payload, resolved_scene_id)

    aliases = build_alias_lookup(
        entity_aliases,
        payload.get("entity_aliases") if isinstance(payload, dict) else None,
    )

    tally = _Tally()
    warnings: list[str] = []
    frames_seen = 0

    for frame in frames:
        if not isinstance(frame, dict):
            continue
        frames_seen += 1
        timestamp = _timestamp(frame)
        confidences = _confidence_index(frame, aliases)

        characters = [c for c in frame.get("characters") or [] if isinstance(c, dict)]
        for entry in characters:
            name = clean(entry.get("name"))
            if not isinstance(name, str):
                continue
            key = ("character", apply_alias(name, aliases))
            tally.appearance(key)
            movement = clean(entry.get("movement"))
            tally.record(
                key,
                {
                    "wears": clean(entry.get("costume")),
                    "screen_position": screen_direction(entry.get("position")),
                    "movement": movement_state(movement) or movement,
                    "emotional_state": clean(entry.get("emotional_state")),
                },
                confidences.get(key, 1.0),
                timestamp,
            )

        for entry in (p for p in frame.get("props") or [] if isinstance(p, dict)):
            name = clean(entry.get("name"))
            if not isinstance(name, str):
                continue
            key = ("prop", apply_alias(name, aliases))
            tally.appearance(key)
            hand = hand_value(entry.get("hand_usage"))
            confidence = confidences.get(key, 1.0)
            tally.record(
                key,
                {
                    "held_in_hand": hand,
                    "prop_state": clean(entry.get("state")),
                    "owner": clean(entry.get("owner")),
                },
                confidence,
                timestamp,
            )

            owner = _infer_owner(entry, characters, aliases, infer_prop_owner)
            if owner is not None:
                tally.record(
                    ("character", owner),
                    {"holds": key[1], "held_in_hand": hand},
                    confidence * _INFERRED_OWNER_FACTOR,
                    timestamp,
                    inferred=True,
                )

    detections = tally.detections()
    if frames_seen and not detections:
        warnings.append(
            f"{resolved_scene_id}: {frames_seen} frames analysed but nothing was detected in them."
        )
    if not aliases and any(name.upper().startswith("PERSON_") for _, name in tally.keys()):
        warnings.append(
            "Vision used anonymous track ids (PERSON_n). Supply entity_aliases "
            "(e.g. {\"PERSON_1\": \"Sarah\"}) so footage can be compared against the script."
        )

    observation: dict[str, Any] = {
        "scene_id": resolved_scene_id,
        "sequence": resolved_sequence,
        "detections": detections,
    }

    return AdaptedPayload(
        payload={"source": SourceType.FOOTAGE.value, "observations": [observation]},
        source=SourceType.FOOTAGE,
        scene_ids=[resolved_scene_id],
        entities=sorted({f"{etype}:{name}" for etype, name in tally.keys()}),
        warnings=warnings,
        frames_analysed=frames_seen,
    )


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #


@dataclass
class _Support:
    """Evidence backing one candidate value of one attribute."""

    confidences: list[float] = field(default_factory=list)
    first_timestamp: str | None = None
    direct_frames: int = 0

    def add(self, confidence: float, timestamp: str | None, inferred: bool) -> None:
        self.confidences.append(max(0.0, min(1.0, confidence)))
        if not inferred:
            self.direct_frames += 1
        if self.first_timestamp is None:
            self.first_timestamp = timestamp

    @property
    def mean_confidence(self) -> float:
        return sum(self.confidences) / len(self.confidences) if self.confidences else 0.0

    @property
    def inferred(self) -> bool:
        """True only when no frame reported this value directly."""
        return self.direct_frames == 0


class _Tally:
    """Votes per (entity, attribute, value) across the frames of one scene."""

    def __init__(self) -> None:
        self._votes: dict[tuple[str, str], dict[str, dict[Any, _Support]]] = {}
        self._appearances: Counter[tuple[str, str]] = Counter()

    def appearance(self, key: tuple[str, str]) -> None:
        self._appearances[key] += 1

    def keys(self) -> list[tuple[str, str]]:
        return list(self._votes) or list(self._appearances)

    def record(
        self,
        key: tuple[str, str],
        attributes: dict[str, Any],
        confidence: float,
        timestamp: str | None,
        inferred: bool = False,
    ) -> None:
        for attribute, value in attributes.items():
            if clean(value) is None:
                continue
            by_value = self._votes.setdefault(key, {}).setdefault(attribute, {})
            by_value.setdefault(value, _Support()).add(confidence, timestamp, inferred)

    def detections(self) -> list[dict[str, Any]]:
        """One detection node per (entity, attribute), carrying its own confidence.

        Repeating the entity across nodes is deliberate: the parser emits one
        fact per leaf attribute and inherits `confidence` from the enclosing
        node, so this is the only way to give each attribute the confidence its
        own evidence earned.
        """
        out: list[dict[str, Any]] = []
        for (entity_type, name), attributes in self._votes.items():
            for attribute, by_value in sorted(attributes.items()):
                value, support, agreement = _winner(by_value)
                if value is None or support is None:
                    continue
                node: dict[str, Any] = {
                    "name": name,
                    "type": entity_type,
                    "confidence": round(support.mean_confidence * agreement, 3),
                    attribute: value,
                }
                if support.first_timestamp is not None:
                    node["timestamp"] = support.first_timestamp
                if support.inferred:
                    # Honour the parser's per-node source override so weaker,
                    # adapter-derived claims get AI-inference trust, not footage.
                    node["source"] = SourceType.AI_INFERENCE.value
                out.append(node)
        return out


def _winner(by_value: dict[Any, _Support]) -> tuple[Any, _Support | None, float]:
    """Modal value plus the share of reporting frames that agreed with it."""
    if not by_value:
        return None, None, 0.0
    total = sum(len(support.confidences) for support in by_value.values())
    value = max(
        by_value,
        key=lambda v: (len(by_value[v].confidences), by_value[v].mean_confidence),
    )
    support = by_value[value]
    agreement = len(support.confidences) / total if total else 0.0
    return value, support, agreement


# --------------------------------------------------------------------------- #
# Frame helpers
# --------------------------------------------------------------------------- #


def _frame_list(payload: Any) -> list[Any]:
    """Accept a scene document, a bare frame list, or a single frame."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("observations", "frames"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    if "frame_id" in payload or "detections" in payload:
        return [payload]
    return []


def _sequence(payload: Any, scene_id: str) -> int:
    if isinstance(payload, dict) and isinstance(payload.get("sequence"), int):
        return int(payload["sequence"])
    return sequence_from(scene_id, 1)


def _timestamp(frame: dict[str, Any]) -> str | None:
    value = clean(frame.get("timestamp"))
    if value is None:
        frame_id = frame.get("frame_id")
        return f"frame {frame_id}" if frame_id is not None else None
    return str(value)


def _confidence_index(frame: dict[str, Any], aliases: dict[str, str]) -> dict[tuple[str, str], float]:
    """Per-entity detector confidence from the frame's `detections` array.

    When one entity appears more than once in a frame the highest confidence
    wins — a second, weaker box for the same person is a detector artefact.
    """
    index: dict[tuple[str, str], float] = {}
    for detection in frame.get("detections") or []:
        if not isinstance(detection, dict):
            continue
        name = clean(detection.get("name"))
        confidence = detection.get("confidence")
        if not isinstance(name, str) or not isinstance(confidence, (int, float)):
            continue
        entity_type = str(clean(detection.get("type")) or "character")
        key = (entity_type, apply_alias(name, aliases))
        index[key] = max(index.get(key, 0.0), float(confidence))
    return index


def _infer_owner(
    prop: dict[str, Any],
    characters: list[dict[str, Any]],
    aliases: dict[str, str],
    enabled: bool,
) -> str | None:
    """Which character is holding this prop, when vision did not say.

    `hand_usage` comes from associating the prop with a detected wrist, so a
    frame containing exactly one person and a prop in a hand identifies the
    holder unambiguously. With two or more people in frame it does not, and
    nothing is inferred.
    """
    stated = clean(prop.get("owner"))
    if isinstance(stated, str):
        return apply_alias(stated, aliases)
    if not enabled or len(characters) != 1:
        return None
    if hand_value(prop.get("hand_usage")) not in {"left", "right", "both"}:
        return None
    name = clean(characters[0].get("name"))
    return apply_alias(name, aliases) if isinstance(name, str) else None
