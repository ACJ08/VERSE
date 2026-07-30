"""MOCK stand-in for team 2 (Video Vision).

No OpenCV, no model. It derives "observations" from the script and then injects
a known set of continuity errors, so the demo has ground truth to check the
engine against. Replace with team 2's real detector output.

Because the errors are declared in `INJECTED_ERRORS`, the demo can assert that
the engine found exactly what was planted — which is how we know the pipeline
works rather than just runs.
"""

from __future__ import annotations

import random
from typing import Any

# (scene_id, character, attribute, wrong_value | None to drop it entirely)
# None means "the detector saw nothing", which should surface as missing_object.
INJECTED_ERRORS: list[tuple[str, str, str, str | None]] = [
    ("SCENE_012", "Sarah", "held_in_hand", "right"),   # mitigated by the panic beat
    ("SCENE_013", "Sarah", "held_in_hand", "right"),   # repeat -> escalates
    ("SCENE_013", "Sarah", "wears", "red cardigan"),   # unexplained costume change
    ("SCENE_013", "Marcus", "screen_position", "frame left"),  # crosses the line
    ("SCENE_015", "Marcus", "holds", None),            # prop vanishes
]

# Vision models are less sure about small/edge details than about costume.
_CONFIDENCE_BY_ATTRIBUTE = {
    "held_in_hand": 0.86,
    "screen_position": 0.90,
    "wears": 0.94,
    "holds": 0.92,
}

_FIELD_NAMES = {
    "held_in_hand": "hand",
    "screen_position": "position",
    "wears": "wears",
    "holds": "holds",
}


def detect(script_json: dict[str, Any], seed: int = 7) -> dict[str, Any]:
    """Produce footage observations in team 2's contract shape."""
    rng = random.Random(seed)
    errors = {(s, c, a): v for s, c, a, v in INJECTED_ERRORS}
    observations: list[dict[str, Any]] = []

    for index, scene in enumerate(script_json.get("scenes", [])):
        scene_id = scene["scene_id"]
        detections: list[dict[str, Any]] = []

        for character in scene.get("characters", []):
            name = character["name"]
            detection: dict[str, Any] = {"name": name, "type": "character"}
            confidences: list[float] = []

            for attribute, value in character.items():
                if attribute in ("name", "type"):
                    continue

                key = (scene_id, name, attribute)
                observed = errors.get(key, value) if key in errors else value
                if observed is None:
                    continue  # detector saw nothing for this attribute

                field = _FIELD_NAMES.get(attribute, attribute)
                detection[field] = observed
                confidences.append(
                    round(
                        min(0.99, _CONFIDENCE_BY_ATTRIBUTE.get(attribute, 0.88)
                            + rng.uniform(-0.04, 0.04)),
                        2,
                    )
                )

            if len(detection) > 2:
                detection["confidence"] = round(sum(confidences) / len(confidences), 2)
                detections.append(detection)

        if detections:
            observations.append(
                {
                    "scene_id": scene_id,
                    "sequence": scene.get("sequence"),
                    "timestamp": _timestamp(index),
                    "detections": detections,
                }
            )

    return {"project_id": "VERSE_DEMO", "source": "footage", "observations": observations}


def _timestamp(index: int) -> str:
    total = 8.4 + index * 23.6
    return f"{int(total // 60):02d}:{total % 60:04.1f}"


def expected_findings() -> list[dict[str, str]]:
    """The planted errors, for the demo to check the engine against."""
    return [
        {
            "scene_id": scene,
            "character": character,
            "attribute": attribute,
            "injected": value if value is not None else "<removed>",
        }
        for scene, character, attribute, value in INJECTED_ERRORS
    ]
