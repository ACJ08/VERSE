"""Adapter tests — the seam between teams 1/2 and the engine.

Fixtures are the real payload shapes (`examples/script_intelligence_response.json`,
`examples/vision_scene_frames.json` trimmed from actual pipeline output), so a
change to either team's format fails here rather than silently producing an
engine that stores facts nobody ever compares.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.adapters import (
    adapt_any,
    adapt_call_sheet,
    adapt_script_intelligence,
    adapt_vision,
    detect_shape,
)
from app.adapters.base import hand_value, movement_state, screen_direction
from app.engine import ContinuityEngine

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def script_response() -> dict[str, Any]:
    return json.loads((EXAMPLES / "script_intelligence_response.json").read_text(encoding="utf-8"))


@pytest.fixture
def vision_frames() -> dict[str, Any]:
    return json.loads((EXAMPLES / "vision_scene_frames.json").read_text(encoding="utf-8"))


def _attributes(payload: dict[str, Any], entity_name: str) -> dict[str, Any]:
    """Collect every attribute emitted for one entity across a scene payload."""
    found: dict[str, Any] = {}
    for scene in payload.get("scenes", []):
        for entry in [*scene.get("characters", []), *scene.get("props", [])]:
            if entry.get("name") == entity_name:
                found.update({k: v for k, v in entry.items() if k not in {"name", "type"}})
    return found


# --------------------------------------------------------------------------- #
# Shape detection
# --------------------------------------------------------------------------- #


def test_detect_shape_distinguishes_all_three_producers(script_response, vision_frames):
    assert detect_shape(script_response) == "script_intelligence"
    assert detect_shape(vision_frames) == "vision"
    assert detect_shape({"call_sheet": {"scenes": ["12"], "cast": ["SARAH - 07:00"]}}) == "call_sheet"


def test_engine_shaped_payload_passes_through_untouched(script_payload):
    adapted = adapt_any(script_payload)
    assert detect_shape(script_payload) == "engine"
    assert adapted.payload is script_payload
    assert adapted.scene_ids == ["SCENE_011", "SCENE_012", "SCENE_013"]


# --------------------------------------------------------------------------- #
# Script intelligence
# --------------------------------------------------------------------------- #


def test_script_adapter_lifts_scene_id_out_of_metadata(script_response):
    adapted = adapt_script_intelligence(script_response)
    assert adapted.scene_ids == ["SCENE_001", "SCENE_002", "SCENE_003"]
    assert [s["sequence"] for s in adapted.payload["scenes"]] == [1, 2, 3]


def test_script_adapter_maps_fields_onto_compared_attributes(script_response):
    payload = adapt_script_intelligence(script_response).payload
    sarah = _attributes(payload, "SARAH")
    assert sarah["wears"] == "grey shirt"                 # last scene wins in this helper
    assert sarah["screen_position"] == "frame right"
    assert sarah["holds"] == "wine glass"
    assert sarah["held_in_hand"] == "right"


def test_script_adapter_keeps_prose_off_compared_attributes(script_response):
    """Prose must not land on `movement`, or it would fight the vision enum."""
    payload = adapt_script_intelligence(script_response).payload
    scene_two = payload["scenes"][1]
    sarah = next(c for c in scene_two["characters"] if c.get("movement_description"))
    assert sarah["movement_description"] == "rises and crosses to the counter"
    assert sarah["movement"] == "moving"


def test_script_adapter_rehomes_prop_owner_onto_the_character(script_response):
    payload = adapt_script_intelligence(script_response).payload
    holdings = [
        c for c in payload["scenes"][0]["characters"] if c.get("holds") == "wine glass"
    ]
    assert holdings, "a prop with an owner must produce a `holds` fact on that character"
    assert holdings[0]["name"] == "SARAH"
    assert holdings[0]["held_in_hand"] == "right"


def test_script_adapter_keeps_notes_out_of_the_fact_stream(script_response):
    adapted = adapt_script_intelligence(script_response)
    assert len(adapted.notes) == 1
    assert adapted.notes[0]["scene_id"] == "SCENE_001"
    serialised = json.dumps(adapted.payload)
    assert "Glass level must match" not in serialised


def test_script_adapter_carries_action_prose_for_assumption_mining(script_response):
    payload = adapt_script_intelligence(script_response).payload
    assert "crowd panics" in payload["scenes"][1]["action"]


def test_script_adapter_drops_empty_values_rather_than_asserting_them():
    response = {
        "scenes": [
            {
                "metadata": {"scene_id": "SCENE_001"},
                "characters": [{"name": "SARAH", "costume": None, "position": "", "movement": "n/a"}],
                "props": [{"name": "glass", "hand_usage": None, "state": "unknown"}],
            }
        ]
    }
    payload = adapt_script_intelligence(response).payload
    character = payload["scenes"][0]["characters"][0]
    assert set(character) == {"name", "type"}
    assert set(payload["scenes"][0]["props"][0]) == {"name", "type"}


def test_script_adapter_warns_about_unusable_scenes():
    adapted = adapt_script_intelligence({"scenes": [{"metadata": {"scene_id": "SCENE_009"}}]})
    assert any("SCENE_009" in w for w in adapted.warnings)


def test_script_adapter_accepts_a_single_scene_object(script_response):
    single = script_response["scenes"][0]
    assert detect_shape(single) == "script_intelligence"
    assert adapt_script_intelligence(single).scene_ids == ["SCENE_001"]


# --------------------------------------------------------------------------- #
# Vision
# --------------------------------------------------------------------------- #


def test_vision_adapter_collapses_frames_to_one_scene_observation(vision_frames):
    adapted = adapt_vision(vision_frames)
    assert len(adapted.payload["observations"]) == 1
    assert adapted.payload["observations"][0]["scene_id"] == "SCENE_001"
    assert adapted.frames_analysed == 8


def test_vision_adapter_discounts_a_flickering_value(vision_frames):
    """The real clip's torso colour flickers black/pink/gray/dark green.

    Whichever value wins the vote, only a minority of frames backed it, so the
    reported confidence has to fall well below the detector's own — low enough
    that `min_observation_confidence` can filter it out rather than the engine
    reporting a wardrobe change that never happened.
    """
    adapted = adapt_vision(vision_frames, entity_aliases={"PERSON_1": "Sarah"})
    wears = [d for d in adapted.payload["observations"][0]["detections"] if "wears" in d]
    sarah = next(d for d in wears if d["name"] == "Sarah")
    assert sarah["wears"] in {"black", "pink"}   # the two joint-modal values
    assert 0.0 < sarah["confidence"] < 0.4


def test_vision_adapter_keeps_confidence_when_every_frame_agrees():
    """A stable observation must not be penalised by the agreement scaling."""
    frames = {
        "scene_id": "SCENE_001",
        "observations": [
            {
                "frame_id": i,
                "timestamp": f"00:00:0{i}.000",
                "characters": [{"name": "PERSON_1", "costume": "navy jacket"}],
                "props": [],
                "detections": [{"type": "character", "name": "PERSON_1", "confidence": 0.9}],
            }
            for i in range(3)
        ],
    }
    adapted = adapt_vision(frames, entity_aliases={"PERSON_1": "Sarah"})
    wears = next(d for d in adapted.payload["observations"][0]["detections"] if "wears" in d)
    assert wears["wears"] == "navy jacket"
    assert wears["confidence"] == pytest.approx(0.9)
    # The earliest supporting frame is cited, not the last one seen.
    assert wears["timestamp"] == "00:00:00.000"


def test_vision_adapter_emits_one_node_per_attribute_with_its_own_confidence(vision_frames):
    adapted = adapt_vision(vision_frames, entity_aliases={"PERSON_1": "Sarah"})
    detections = adapted.payload["observations"][0]["detections"]
    sarah_nodes = [d for d in detections if d["name"] == "Sarah"]
    attributes = {k for node in sarah_nodes for k in node if k not in
                  {"name", "type", "confidence", "timestamp", "source"}}
    assert {"wears", "screen_position", "held_in_hand", "holds"} <= attributes
    # Each node carries exactly one attribute, so confidences cannot be conflated.
    for node in sarah_nodes:
        payload_keys = set(node) - {"name", "type", "confidence", "timestamp", "source"}
        assert len(payload_keys) == 1


def test_vision_adapter_applies_entity_aliases(vision_frames):
    adapted = adapt_vision(vision_frames, entity_aliases={"PERSON_1": "Sarah"})
    assert "character:Sarah" in adapted.entities
    assert "character:PERSON_1" not in adapted.entities


def test_vision_adapter_accepts_canonical_to_alias_direction(vision_frames):
    adapted = adapt_vision(vision_frames, entity_aliases={"Sarah": ["PERSON_1", "PERSON_3"]})
    assert "character:Sarah" in adapted.entities
    assert "character:PERSON_3" not in adapted.entities


def test_vision_adapter_warns_when_track_ids_are_unmapped(vision_frames):
    adapted = adapt_vision(vision_frames)
    assert any("PERSON_n" in w for w in adapted.warnings)


def test_vision_adapter_infers_the_prop_holder_only_when_unambiguous(vision_frames):
    """One person in frame plus a prop in a hand identifies the holder."""
    adapted = adapt_vision(vision_frames, entity_aliases={"PERSON_1": "Sarah"})
    holds = [d for d in adapted.payload["observations"][0]["detections"] if "holds" in d]
    assert holds and holds[0]["name"] == "Sarah"
    # Inferred, so it must declare the weaker source rather than pose as footage.
    assert holds[0]["source"] == "ai_inference"


def test_vision_adapter_does_not_infer_a_holder_with_two_people_in_frame():
    frames = {
        "scene_id": "SCENE_001",
        "observations": [
            {
                "frame_id": 0,
                "timestamp": "00:00:01.000",
                "characters": [{"name": "PERSON_1"}, {"name": "PERSON_2"}],
                "props": [{"name": "glass", "hand_usage": "left"}],
                "detections": [
                    {"type": "character", "name": "PERSON_1", "confidence": 0.9},
                    {"type": "character", "name": "PERSON_2", "confidence": 0.9},
                    {"type": "prop", "name": "glass", "confidence": 0.9},
                ],
            }
        ],
    }
    detections = adapt_vision(frames).payload["observations"][0]["detections"]
    assert not [d for d in detections if "holds" in d]


def test_vision_adapter_keeps_the_timestamp_as_the_source_reference(vision_frames):
    adapted = adapt_vision(vision_frames)
    assert all(
        d["timestamp"].startswith("00:00:")
        for d in adapted.payload["observations"][0]["detections"]
        if "timestamp" in d
    )


def test_vision_adapter_accepts_a_bare_frame_list(vision_frames):
    adapted = adapt_vision(vision_frames["observations"], scene_id="SCENE_042")
    assert adapted.scene_ids == ["SCENE_042"]
    assert adapted.payload["observations"][0]["sequence"] == 42


# --------------------------------------------------------------------------- #
# Call sheets
# --------------------------------------------------------------------------- #


def test_call_sheet_adapter_expands_scene_numbers_and_strips_call_times():
    adapted = adapt_call_sheet(
        {
            "filename": "day12.pdf",
            "call_sheet": {
                "date": "2026-03-04",
                "location": "STAGE 4",
                "scenes": ["12", "SC 13"],
                "cast": ["SARAH - 07:00", "MARCUS  08:30"],
                "shooting_time": "06:30",
            },
        }
    )
    assert adapted.scene_ids == ["SCENE_012", "SCENE_013"]
    assert adapted.entities == ["character:MARCUS", "character:SARAH"]
    assert adapted.payload["scenes"][0]["location"] == "STAGE 4"
    assert adapted.source.value == "call_sheet"


def test_call_sheet_adapter_warns_when_no_scenes_are_listed():
    adapted = adapt_call_sheet({"call_sheet": {"location": "STAGE 4", "scenes": []}})
    assert adapted.warnings and not adapted.payload["scenes"]


# --------------------------------------------------------------------------- #
# Value normalisation helpers
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "text,expected",
    [
        ("left", "frame left"),
        ("center", "frame centre"),
        ("seated frame right", "frame right"),
        ("by the door", None),
        ("moves left to right", None),  # a move, not a position
        (None, None),
    ],
)
def test_screen_direction(text, expected):
    assert screen_direction(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("stationary", "stationary"),
        ("moving", "moving"),
        ("crosses to the window", "moving"),
        ("stands still", "stationary"),
        ("remains seated", "stationary"),
        ("looks worried", None),
    ],
)
def test_movement_state(text, expected):
    assert movement_state(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [("left", "left"), ("Right Hand", "right"), ("both hands", "both"), ("none", "none"), ("", None)],
)
def test_hand_value(text, expected):
    assert hand_value(text) == expected


# --------------------------------------------------------------------------- #
# Adapters through the engine
# --------------------------------------------------------------------------- #


def test_script_and_vision_payloads_meet_on_the_same_entities(script_response, vision_frames):
    engine = ContinuityEngine()
    engine.ingest_script(adapt_script_intelligence(script_response).payload)
    engine.ingest_footage(
        adapt_vision(vision_frames, entity_aliases={"PERSON_1": "SARAH"}).payload
    )

    entities = engine.graph.entities()
    assert "sarah" in entities
    assert "marcus" in entities
    # Facts from both producers must land on the same node, or nothing compares.
    sources = {f.source.type.value for f in engine.graph.facts_for_entity("sarah")}
    assert {"script", "footage"} <= sources


def test_costume_colour_is_not_reported_as_a_wardrobe_error(script_response, vision_frames):
    """Vision sees "black"; the script says "black dress". Same claim, less detail."""
    engine = ContinuityEngine()
    engine.ingest_script(adapt_script_intelligence(script_response).payload)
    engine.ingest_footage(
        adapt_vision(vision_frames, entity_aliases={"PERSON_1": "SARAH"}).payload
    )
    report = engine.analyse("SCENE_001")
    assert not [i for i in report.issues if i.type == "costume_mismatch"]


def test_hand_disagreement_between_script_and_footage_is_detected(script_response):
    """Script says the glass is in the right hand; footage says left, confidently."""
    engine = ContinuityEngine()
    engine.ingest_script(adapt_script_intelligence(script_response).payload)
    footage = {
        "scene_id": "SCENE_001",
        "observations": [
            {
                "frame_id": 0,
                "timestamp": "00:00:04.000",
                "characters": [{"name": "PERSON_1"}],
                "props": [{"name": "wine glass", "hand_usage": "left"}],
                "detections": [
                    {"type": "character", "name": "PERSON_1", "confidence": 0.95},
                    {"type": "prop", "name": "wine glass", "confidence": 0.95},
                ],
            }
        ],
    }
    engine.ingest_footage(adapt_vision(footage, entity_aliases={"PERSON_1": "SARAH"}).payload)
    report = engine.analyse("SCENE_001")
    assert any(i.type == "hand_mismatch" for i in report.issues)


def test_envelope_keys_do_not_become_facts(script_response):
    """`project_id`, `filename` and friends describe the payload, not the film."""
    engine = ContinuityEngine()
    payload = adapt_script_intelligence(script_response).payload
    payload["project_id"] = "VERSE_DEMO"
    payload["filename"] = "coffee_shop.pdf"
    facts = engine.ingest_script(payload)
    assert not [f for f in facts if f.attribute in {"project_id", "filename", "type"}]
    assert not [f for f in facts if f.entity.name == "unknown_scene"]
