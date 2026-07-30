"""Derived-view tests — the read models the dashboard renders.

These cover the guarantees the UI depends on: a scene's score matches the
project's scoring, scene metadata is not polluted by entity attributes, and a
slot's state distinguishes "verified" from "not shot yet" from "differs but was
too weak to flag".
"""

from __future__ import annotations

from app.engine import ContinuityEngine
from app.models.schemas import AttributeState, SourceType
from app.reporting.views import entity_views, project_overview, scene_views

from .conftest import footage_scene, script_scene


def test_scene_views_are_in_screenplay_order_not_ingestion_order(engine: ContinuityEngine):
    engine.ingest_script(script_scene("SCENE_030", 30, wears="red coat"))
    engine.ingest_script(script_scene("SCENE_010", 10, wears="blue coat"))
    engine.analyse()
    assert [s.scene_id for s in scene_views(engine)] == ["SCENE_010", "SCENE_030"]


def test_scene_view_reports_location_of_the_scene_not_of_its_props(engine: ContinuityEngine):
    """A prop's `location` ("table") must not be reported as the scene's."""
    engine.ingest_script(
        {
            "scenes": [
                {
                    "scene_id": "SCENE_001",
                    "sequence": 1,
                    "location": "coffee shop",
                    "props": [{"name": "glass", "type": "prop", "location": "table"}],
                }
            ]
        }
    )
    engine.analyse()
    assert scene_views(engine)[0].location == "coffee shop"


def test_scene_view_marks_unshot_scenes_and_explains_itself(engine: ContinuityEngine):
    engine.ingest_script(script_scene("SCENE_001", 1, wears="blue coat"))
    engine.analyse()
    view = scene_views(engine)[0]
    assert view.has_footage is False
    assert view.sources == [SourceType.SCRIPT]
    assert "Not shot yet" in view.headline
    assert view.score == 100.0


def test_scene_view_score_matches_the_report_for_a_single_scene(engine: ContinuityEngine):
    engine.ingest_script(script_scene("SCENE_001", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("SCENE_001", 1, hand="right"))
    report = engine.analyse()
    view = scene_views(engine, report.issues)[0]
    assert view.score == report.overall_score
    assert view.issue_count == len(report.issues)
    assert view.has_footage is True
    assert "mismatch" in view.headline.lower()


def test_scene_view_isolates_issues_per_scene(engine: ContinuityEngine):
    engine.ingest_script(script_scene("SCENE_001", 1, held_in_hand="left"))
    engine.ingest_script(script_scene("SCENE_002", 2, held_in_hand="left"))
    engine.ingest_footage(footage_scene("SCENE_002", 2, hand="right"))
    report = engine.analyse()
    views = {v.scene_id: v for v in scene_views(engine, report.issues)}
    assert views["SCENE_001"].issue_count == 0
    assert views["SCENE_002"].issue_count >= 1
    assert views["SCENE_001"].score > views["SCENE_002"].score


def test_project_overview_counts_shot_and_clean_scenes(engine: ContinuityEngine):
    engine.ingest_script(script_scene("SCENE_001", 1, held_in_hand="left"))
    engine.ingest_script(script_scene("SCENE_002", 2, held_in_hand="left"))
    engine.ingest_footage(footage_scene("SCENE_002", 2, hand="right"))
    report = engine.analyse()
    overview = project_overview(engine, scene_views(engine, report.issues))
    assert overview["scenes_total"] == 2
    assert overview["scenes_shot"] == 1
    assert overview["scenes_clean"] == 0
    assert overview["issues_total"] == len(report.issues)
    assert "props" in overview["categories_at_risk"]


# --------------------------------------------------------------------------- #
# Entity views
# --------------------------------------------------------------------------- #


def test_entity_view_states_cover_the_four_cases(engine: ContinuityEngine):
    engine.ingest_script(script_scene("SCENE_001", 1, wears="blue coat", held_in_hand="left"))
    engine.ingest_footage(
        footage_scene("SCENE_001", 1, wears="blue coat", hand="right", movement="moving")
    )
    report = engine.analyse()
    slots = {s.attribute: s for v in entity_views(engine, report.issues) for s in v.slots}

    assert slots["wears"].state is AttributeState.MATCH
    assert slots["held_in_hand"].state is AttributeState.CONFLICT
    assert slots["held_in_hand"].flagged is True
    assert slots["held_in_hand"].issue_id is not None
    # Footage saw movement the script never mentioned.
    assert slots["movement"].state is AttributeState.OBSERVED_ONLY


def test_entity_view_marks_expectations_with_no_footage_as_unverified(engine: ContinuityEngine):
    engine.ingest_script(script_scene("SCENE_001", 1, wears="blue coat"))
    engine.analyse()
    slot = entity_views(engine)[0].slots[0]
    assert slot.state is AttributeState.UNVERIFIED
    assert slot.observed is None
    assert slot.flagged is False


def test_unflagged_conflict_is_distinguishable_from_a_flagged_one(engine: ContinuityEngine):
    """A low-confidence disagreement is recorded but must not read as an error."""
    engine.ingest_script(script_scene("SCENE_001", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("SCENE_001", 1, hand="right", confidence=0.4))
    report = engine.analyse()
    slot = next(
        s for v in entity_views(engine, report.issues) for s in v.slots
        if s.attribute == "held_in_hand"
    )
    assert slot.state is AttributeState.CONFLICT
    assert slot.flagged is False
    assert slot.issue_id is None


def test_entity_view_carries_both_halves_with_their_sources(engine: ContinuityEngine):
    engine.ingest_script(script_scene("SCENE_001", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("SCENE_001", 1, hand="right", timestamp="00:14.2"))
    report = engine.analyse()
    slot = next(
        s for v in entity_views(engine, report.issues) for s in v.slots
        if s.attribute == "held_in_hand"
    )
    assert slot.expected.source is SourceType.SCRIPT
    assert slot.observed.source is SourceType.FOOTAGE
    assert slot.observed.source_reference == "00:14.2"


def test_entity_views_can_be_filtered_for_the_costume_screen(engine: ContinuityEngine):
    engine.ingest_script(
        {
            "scenes": [
                {
                    "scene_id": "SCENE_001",
                    "sequence": 1,
                    "characters": [{"name": "Sarah", "type": "character", "wears": "blue coat"}],
                    "props": [{"name": "glass", "type": "prop", "held_in_hand": "left"}],
                }
            ]
        }
    )
    engine.analyse()

    costumes = entity_views(engine, entity_types={"character"}, attributes={"wears"})
    assert [v.entity.name for v in costumes] == ["Sarah"]
    assert {s.attribute for v in costumes for s in v.slots} == {"wears"}

    props = entity_views(engine, entity_types={"prop"})
    assert [v.entity.name for v in props] == ["glass"]


def test_entity_view_latest_tracks_the_current_belief_across_scenes(engine: ContinuityEngine):
    engine.ingest_script(script_scene("SCENE_001", 1, wears="blue coat"))
    engine.ingest_script(script_scene("SCENE_002", 2, wears="grey shirt"))
    engine.analyse()
    view = entity_views(engine)[0]
    assert view.latest["wears"] == "grey shirt"
    assert view.scene_ids == ["SCENE_001", "SCENE_002"]


def test_entity_views_exclude_scene_envelope_attributes(engine: ContinuityEngine):
    engine.ingest_script(
        {
            "scenes": [
                {
                    "scene_id": "SCENE_001",
                    "sequence": 1,
                    "slugline": "INT. COFFEE SHOP - DAY",
                    "action": "Sarah waits.",
                    "characters": [{"name": "Sarah", "type": "character", "wears": "blue coat"}],
                }
            ]
        }
    )
    engine.analyse()
    attributes = {s.attribute for v in entity_views(engine) for s in v.slots}
    assert attributes == {"wears"}
