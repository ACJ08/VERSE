"""Conflict detection, assumptions and narrative reasoning.

Covers plan test cases 1-8 and 12-14.
"""

from __future__ import annotations

from app.engine import ContinuityEngine
from app.models.schemas import Category, Severity

from .conftest import find_issue, footage_scene, issue_types, script_scene


def test_matching_values_produce_no_issue(engine: ContinuityEngine):
    """Case 1."""
    engine.ingest_script(script_scene("S1", 1, held_in_hand="left", wears="blue blazer"))
    engine.ingest_footage(footage_scene("S1", 1, hand="left", wears="blue blazer"))

    report = engine.analyse("S1")
    assert report.issues == []
    assert report.overall_score == 100.0


def test_wrong_hand_produces_hand_mismatch(engine: ContinuityEngine):
    """Case 2 — the First Working Milestone."""
    engine.ingest_script(script_scene("S1", 1, holds="glass", held_in_hand="left"))
    engine.ingest_footage(footage_scene("S1", 1, holds="glass", hand="right"))

    issue = find_issue(engine.analyse("S1"), "hand_mismatch")
    assert issue is not None
    assert issue.category is Category.PROPS
    assert issue.expected.value == "left"
    assert issue.observed.value == "right"
    assert issue.expected.source.value == "script"
    assert issue.observed.source.value == "footage"


def test_missing_prop_produces_missing_object(engine: ContinuityEngine):
    """Case 3."""
    engine.ingest_script(script_scene("S1", 1, holds="glass"))
    engine.ingest_footage(footage_scene("S1", 1, wears="blue blazer"))  # scene was filmed

    assert "missing_object" in issue_types(engine.analyse("S1"))


def test_missing_prop_is_silent_before_footage_arrives(engine: ContinuityEngine):
    """Absence of footage is not evidence of a missing prop."""
    engine.ingest_script(script_scene("S1", 1, holds="glass"))

    assert "missing_object" not in issue_types(engine.analyse("S1"))


def test_unexplained_costume_change_is_flagged(engine: ContinuityEngine):
    """Case 4."""
    engine.ingest_script(script_scene("S1", 1, wears="blue blazer"))
    engine.ingest_footage(footage_scene("S2", 2, wears="red coat"))

    issue = find_issue(engine.analyse("S2"), "costume_mismatch")
    assert issue is not None
    assert issue.category is Category.COSTUME


def test_explicit_costume_change_prevents_false_warning(engine: ContinuityEngine):
    """Case 5: 'Sarah removes her blue blazer' justifies the change."""
    engine.ingest_script(script_scene("S1", 1, wears="blue blazer"))
    engine.ingest_script(
        script_scene("S2", 2, wears="grey shirt", action="Sarah removes her blue blazer.")
    )
    engine.ingest_footage(footage_scene("S2", 2, wears="grey shirt"))

    assert "costume_mismatch" not in issue_types(engine.analyse("S2"))


def test_panic_scene_creates_temporary_assumption(engine: ContinuityEngine):
    """Case 6."""
    engine.ingest_script(
        script_scene("S1", 1, holds="glass", action="The crowd panics and rushes through the shop.")
    )

    report = engine.analyse("S1")
    assert report.temporary_assumptions, "panic should create an environmental assumption"

    assumption = report.temporary_assumptions[0]
    assert Category.PROPS in assumption.affects_categories
    assert assumption.is_active_at(1)
    assert not assumption.is_active_at(99), "assumptions must expire"


def test_trigger_words_need_whole_word_match(engine: ContinuityEngine):
    """Regression: 'window' contained 'wind' and raised a false storm assumption.

    Spurious assumptions silently discount real issues, so this matters more
    than it looks.
    """
    engine.ingest_script(
        script_scene("S1", 1, holds="glass", action="Sarah sits by the window and waits.")
    )

    report = engine.analyse("S1")
    assert report.temporary_assumptions == []


def test_assumption_does_not_lower_severity(engine: ContinuityEngine):
    """Regression: mitigation was applied twice (severity *and* score impact).

    Severity describes the error type; only the score reflects justification.
    """
    engine.ingest_script(
        script_scene(
            "S1", 1, held_in_hand="left",
            action="The crowd panics and rushes through the shop.",
        )
    )
    engine.ingest_footage(footage_scene("S1", 1, hand="right"))

    issue = find_issue(engine.analyse("S1"), "hand_mismatch")
    assert issue is not None
    assert issue.mitigated_by
    assert issue.severity is Severity.MEDIUM, "severity is intrinsic to the error type"


def test_assumption_reduces_score_impact(engine: ContinuityEngine):
    """A narrative justification should soften, not silence, the issue."""
    calm = ContinuityEngine(config=engine.config)
    calm.ingest_script(script_scene("S1", 1, screen_position="frame left"))
    calm.ingest_footage(footage_scene("S1", 1, position="frame right"))
    baseline = find_issue(calm.analyse("S1"), "screen_direction_mismatch")

    chaotic = ContinuityEngine(config=engine.config)
    chaotic.ingest_script(
        script_scene(
            "S1", 1, screen_position="frame left",
            action="The crowd panics and rushes through the shop.",
        )
    )
    chaotic.ingest_footage(footage_scene("S1", 1, position="frame right"))
    softened = find_issue(chaotic.analyse("S1"), "screen_direction_mismatch")

    assert baseline is not None and softened is not None
    assert softened.mitigated_by, "issue should cite the assumption that softened it"
    assert softened.score_impact < baseline.score_impact


def test_low_confidence_observation_is_ignored(engine: ContinuityEngine):
    """Below the observation threshold, the vision output is not trusted at all."""
    engine.ingest_script(script_scene("S1", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("S1", 1, hand="right", confidence=0.1))

    assert "hand_mismatch" not in issue_types(engine.analyse("S1"))


def test_repeated_issue_increases_severity(engine: ContinuityEngine):
    """Case 8."""
    for scene in (1, 2, 3):
        engine.ingest_script(script_scene(f"S{scene}", scene, held_in_hand="left"))
        engine.ingest_footage(footage_scene(f"S{scene}", scene, hand="right"))

    report = engine.analyse()
    mismatches = [i for i in report.issues if i.type == "hand_mismatch"]
    assert len(mismatches) == 3

    first, last = mismatches[0], mismatches[-1]
    assert last.occurrences > first.occurrences
    assert _rank(last.severity) > _rank(first.severity), "repeats must escalate"


def test_nearby_history_outranks_distant_history(engine: ContinuityEngine):
    """Case 13: the most recent expectation governs."""
    engine.ingest_script(script_scene("S1", 1, wears="blue blazer"))
    engine.ingest_script(script_scene("S9", 9, wears="grey shirt"))
    engine.ingest_footage(footage_scene("S10", 10, wears="grey shirt"))

    assert "costume_mismatch" not in issue_types(engine.analyse("S10"))


def test_sources_are_shown_for_both_halves(engine: ContinuityEngine):
    """Case 14."""
    engine.ingest_script(script_scene("S1", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("S1", 1, hand="right", timestamp="00:14.2"))

    issue = find_issue(engine.analyse("S1"), "hand_mismatch")
    assert issue is not None
    assert issue.expected.source_reference
    assert issue.observed.source_reference == "00:14.2"
    assert issue.supporting_fact_ids


def test_custom_attribute_conflict_is_caught(engine: ContinuityEngine):
    """Novel attributes from teams 1 and 2 still get checked."""
    engine.ingest_script(script_scene("S1", 1, umbrella_state="open"))
    engine.ingest_footage(footage_scene("S1", 1, umbrella_state="closed"))

    issue = find_issue(engine.analyse("S1"), "custom_attribute_conflict")
    assert issue is not None
    assert issue.category is Category.OTHER


def _rank(severity: Severity) -> int:
    return [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL].index(severity)
