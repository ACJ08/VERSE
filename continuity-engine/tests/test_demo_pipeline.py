"""End-to-end guard over the full demo pipeline.

The mock detector plants a known set of errors, so this asserts the engine
finds exactly those and stays quiet everywhere else. It is the closest thing
we have to ground truth until real team data arrives.

Skipped automatically if the demo folder is absent (e.g. engine published alone).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytest.importorskip("demo.pipeline", reason="demo package not present")

from demo.mocks import vision_detector  # noqa: E402
from demo.pipeline import build_engine  # noqa: E402


@pytest.fixture(scope="module")
def report():
    engine, _, _ = build_engine()
    return engine.analyse()


def test_every_planted_error_is_detected(report):
    for planted in vision_detector.expected_findings():
        assert any(
            issue.scene_id == planted["scene_id"]
            and issue.entity.name.lower() == planted["character"].lower()
            for issue in report.issues
        ), f"missed planted error: {planted}"


def test_no_issues_in_the_clean_scene(report):
    """Scene 11 has script and footage in agreement."""
    assert [i for i in report.issues if i.scene_id == "SCENE_011"] == []


def test_explicit_costume_change_is_not_flagged(report):
    """Scene 14: 'Sarah removes her blue blazer' explains the grey shirt."""
    assert [
        i for i in report.issues if i.scene_id == "SCENE_014" and i.attribute == "wears"
    ] == []


def test_characters_are_not_confused(report):
    """Each issue must belong to the character the error was planted on."""
    planted = {(p["scene_id"], p["character"]) for p in vision_detector.expected_findings()}
    for issue in report.issues:
        assert (issue.scene_id, issue.entity.name) in planted, (
            f"{issue.type} in {issue.scene_id} attributed to {issue.entity.name}, "
            "which had no planted error"
        )


def test_repeated_error_escalates(report):
    """Sarah's hand mismatch appears in scenes 12 and 13."""
    repeats = [i for i in report.issues if i.type == "hand_mismatch" and i.occurrences > 1]
    assert repeats, "the repeated hand mismatch should have escalated"


def test_pipeline_is_deterministic():
    """Two runs of the same inputs must produce the same score."""
    first, _, _ = build_engine()
    second, _, _ = build_engine()
    assert first.analyse().overall_score == second.analyse().overall_score
