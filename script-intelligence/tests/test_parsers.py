"""
VERSE Test Suite - Scene Splitter and Document Parser Tests.
"""

import os
import tempfile
import pytest

from app.parsers.scene_splitter import split_into_scenes, parse_scene_metadata
from app.parsers.document_parser import extract_text, extract_txt
from app.utils.text_utils import (
    clean_screenplay_text,
    extract_action_prose,
    truncate_scene_text,
)


def test_split_into_scenes_basic(sample_screenplay_text):
    scenes = split_into_scenes(sample_screenplay_text)
    assert len(scenes) == 2
    assert scenes[0].startswith("INT. SARAH'S APARTMENT")
    assert scenes[1].startswith("EXT. ALLEYWAY")


def test_split_into_scenes_various_sluglines():
    text = """\
101 INT. LIVING ROOM - DAY
First scene body.

EXT. GARDEN - NIGHT
Second scene body.

INT./EXT. CAR - MOVING - DAY
Third scene body.

I/E. CAFE - DAWN
Fourth scene body.
"""
    scenes = split_into_scenes(text)
    assert len(scenes) == 4
    assert "LIVING ROOM" in scenes[0]
    assert "GARDEN" in scenes[1]
    assert "CAR" in scenes[2]
    assert "CAFE" in scenes[3]


def test_parse_scene_metadata():
    heading = "INT. SARAH'S APARTMENT - KITCHEN - NIGHT"
    meta = parse_scene_metadata(heading, scene_id="SCENE_001")
    assert meta.scene_id == "SCENE_001"
    assert meta.interior_exterior == "INT."
    assert meta.location == "SARAH'S APARTMENT"
    assert meta.sub_location == "KITCHEN"
    assert meta.time == "NIGHT"


def test_clean_screenplay_text():
    raw = "Line 1  \r\n\r\n-----\r\nLine 2\r\n\r\n\r\nLine 3"
    cleaned = clean_screenplay_text(raw)
    assert "-----" not in cleaned
    assert "\r" not in cleaned
    assert cleaned == "Line 1\n\nLine 2\n\nLine 3"


def test_truncate_scene_text():
    text = "A" * 100
    truncated = truncate_scene_text(text, max_chars=50, strategy="head")
    assert len(truncated) < 100
    assert "[...truncated...]" in truncated


def test_extract_action_prose_keeps_description_and_drops_dialogue():
    """`SceneContinuity.action` feeds downstream continuity reasoning.

    The continuity engine mines this prose for scripted state changes and for
    narrative events that can explain a discrepancy, so description lines must
    survive and dialogue must not dilute them.
    """
    scene = """\
INT. COFFEE SHOP - DAY

Sarah sits by the window. She picks up a glass with her left hand.

SARAH
Are you sure about this?

MARCUS
(quietly)
No.

The crowd panics and rushes through the shop. Sarah removes her blue blazer.

CUT TO:
"""
    action = extract_action_prose(scene)

    assert action.startswith("Sarah sits by the window.")
    assert "crowd panics" in action           # narrative trigger
    assert "removes her blue blazer" in action  # scripted state change
    assert "Are you sure about this?" not in action
    assert "INT. COFFEE SHOP" not in action   # slug line lives in SceneMetadata
    assert "(quietly)" not in action
    assert "CUT TO" not in action


def test_extract_action_prose_is_truncated_and_handles_empty_input():
    assert extract_action_prose("") == ""
    assert extract_action_prose("   \n\n  ") == ""
    long_scene = "INT. ROOM - DAY\n\n" + ("She waits. " * 400)
    assert len(extract_action_prose(long_scene, max_chars=100)) == 100


def test_extract_txt_file():
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Test screenplay content.")
        path = f.name

    try:
        content = extract_text(path)
        assert content == "Test screenplay content."
    finally:
        if os.path.exists(path):
            os.remove(path)
