"""Scoring, reporting and human-in-the-loop behaviour.

Covers plan test cases 7, 9, 10 and 15.
"""

from __future__ import annotations

from app.config import ProjectConfig
from app.engine import ContinuityEngine
from app.models.schemas import FactOverride, FeedbackAction, IssueStatus, SourceType

from .conftest import find_issue, footage_scene, issue_types, script_scene


def test_clean_scene_scores_100(engine: ContinuityEngine):
    engine.ingest_script(script_scene("S1", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("S1", 1, hand="left"))

    report = engine.analyse("S1")
    assert report.overall_score == 100.0
    assert all(score == 100.0 for score in report.category_scores.values())
    assert "No continuity issues" in report.score_summary.main_reason


def test_low_confidence_issue_has_smaller_score_impact(config: ProjectConfig):
    """Case 7."""
    def impact(confidence: float) -> float:
        engine = ContinuityEngine(config=config)
        engine.ingest_script(script_scene("S1", 1, held_in_hand="left"))
        engine.ingest_footage(footage_scene("S1", 1, hand="right", confidence=confidence))
        issue = find_issue(engine.analyse("S1"), "hand_mismatch")
        assert issue is not None, f"expected an issue at confidence {confidence}"
        return issue.score_impact

    assert impact(0.5) < impact(0.99)


def test_category_and_overall_scores_are_computed(engine: ContinuityEngine):
    """Case 15."""
    engine.ingest_script(script_scene("S1", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("S1", 1, hand="right"))

    report = engine.analyse("S1")
    assert report.category_scores["props"] < 100.0
    assert report.category_scores["costume"] == 100.0, "unaffected categories stay clean"
    assert 0.0 <= report.overall_score < 100.0
    assert report.score_summary.main_reason


def test_only_the_affected_category_is_penalised(engine: ContinuityEngine):
    engine.ingest_script(script_scene("S1", 1, wears="blue blazer"))
    engine.ingest_footage(footage_scene("S2", 2, wears="red coat"))

    report = engine.analyse("S2")
    assert report.category_scores["costume"] < 100.0
    assert report.category_scores["props"] == 100.0


def test_human_confirmed_fact_overrides_ai_output(engine: ContinuityEngine):
    """Case 9."""
    engine.ingest_script(script_scene("S1", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("S1", 1, hand="right"))
    assert "hand_mismatch" in issue_types(engine.analyse("S1"))

    engine.override_fact(
        FactOverride(
            entity_key="sarah",
            attribute="held_in_hand",
            value="right",
            scene_id="S1",
            reason="Director approved the change on set.",
        )
    )

    state = engine.memory.slot_state("sarah", "held_in_hand", "S1")
    assert state.expected is not None
    assert state.expected.source.type is SourceType.HUMAN
    assert state.expected.value == "right"
    assert "hand_mismatch" not in issue_types(engine.analyse("S1"))


def test_dismissed_issue_stops_future_penalties(engine: ContinuityEngine):
    """Case 10."""
    engine.ingest_script(script_scene("S1", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("S1", 1, hand="right"))

    issue = find_issue(engine.analyse("S1"), "hand_mismatch")
    assert issue is not None

    engine.apply_feedback(
        FeedbackAction(issue_id=issue.issue_id, action="dismiss", note="Intentional.")
    )

    engine.ingest_script(script_scene("S2", 2, held_in_hand="left"))
    engine.ingest_footage(footage_scene("S2", 2, hand="right"))
    report = engine.analyse()

    assert "hand_mismatch" not in issue_types(report)
    assert report.overall_score == 100.0


def test_dismissal_is_recorded_not_deleted(engine: ContinuityEngine):
    engine.ingest_script(script_scene("S1", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("S1", 1, hand="right"))
    issue = find_issue(engine.analyse("S1"), "hand_mismatch")
    assert issue is not None

    engine.apply_feedback(FeedbackAction(issue_id=issue.issue_id, action="dismiss"))

    assert engine.feedback.history, "the decision must remain in history"
    assert engine.feedback.history[0].action == "dismiss"


def test_confirming_an_issue_preserves_its_status_across_reruns(engine: ContinuityEngine):
    engine.ingest_script(script_scene("S1", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("S1", 1, hand="right"))
    issue = find_issue(engine.analyse("S1"), "hand_mismatch")
    assert issue is not None

    engine.apply_feedback(FeedbackAction(issue_id=issue.issue_id, action="confirm"))
    rerun = find_issue(engine.analyse("S1"), "hand_mismatch")

    assert rerun is not None
    assert rerun.status is IssueStatus.CONFIRMED


def test_fact_override_keeps_edit_history(engine: ContinuityEngine):
    engine.ingest_script(script_scene("S1", 1, wears="blue blazer"))
    engine.override_fact(
        FactOverride(entity_key="sarah", attribute="wears", value="red coat", scene_id="S1")
    )
    updated = engine.override_fact(
        FactOverride(
            entity_key="sarah", attribute="wears", value="green coat",
            scene_id="S1", reason="corrected",
        )
    )

    assert updated.value == "green coat"
    assert any(edit.previous_value == "red coat" for edit in updated.history)


def test_explanation_cites_its_sources(engine: ContinuityEngine):
    engine.ingest_script(script_scene("S1", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("S1", 1, hand="right", timestamp="00:14.2"))

    issue = find_issue(engine.analyse("S1"), "hand_mismatch")
    assert issue is not None
    assert "script" in issue.explanation
    assert "00:14.2" in issue.explanation
    assert issue.suggested_fix
