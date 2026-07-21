"""Knowledge graph, timeline and trust-based memory resolution."""

from __future__ import annotations

from app.config import ProjectConfig
from app.engine import ContinuityEngine
from app.graph.storage import FactStore
from app.graph.timeline import Timeline
from app.models.schemas import SourceType

from .conftest import footage_scene, script_scene


def test_timeline_orders_scenes_by_screenplay_not_arrival():
    timeline = Timeline()
    timeline.add("SCENE_012", 12)
    timeline.add("SCENE_003", 3)
    timeline.add("SCENE_007", 7)

    assert [n.scene_id for n in timeline.ordered()] == ["SCENE_003", "SCENE_007", "SCENE_012"]


def test_timeline_infers_sequence_from_scene_id():
    timeline = Timeline()
    assert timeline.add("SCENE_012").sequence == 12


def test_proximity_decays_with_narrative_distance():
    timeline = Timeline()
    for n in (1, 2, 10):
        timeline.add(f"SCENE_{n:03d}", n)

    near = timeline.proximity("SCENE_001", "SCENE_002")
    far = timeline.proximity("SCENE_001", "SCENE_010")
    assert timeline.proximity("SCENE_001", "SCENE_001") == 1.0
    assert near > far


def test_conflicting_facts_are_both_preserved(engine: ContinuityEngine):
    """Case: the graph stores both claims rather than overwriting one."""
    engine.ingest_script(script_scene("S1", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("S1", 1, hand="right"))

    facts = engine.graph.facts_for("sarah", "held_in_hand", "S1")
    values = {f.value for f in facts}
    assert values == {"left", "right"}, "both conflicting values must survive ingestion"


def test_memory_resolves_expected_by_trust_not_recency(engine: ContinuityEngine):
    engine.ingest_footage(footage_scene("S1", 1, wears="grey shirt"))
    engine.ingest_script(script_scene("S1", 1, wears="blue blazer"))

    state = engine.memory.slot_state("sarah", "wears", "S1")
    assert state.expected is not None and state.expected.source.type is SourceType.SCRIPT
    assert state.observed is not None and state.observed.source.type is SourceType.FOOTAGE


def test_expectation_carries_forward_to_later_scenes(engine: ContinuityEngine):
    """Continuity is about state persisting when the script says nothing new."""
    engine.ingest_script(script_scene("S1", 1, wears="blue blazer"))
    engine.ingest_footage(footage_scene("S2", 2, wears="red coat"))

    state = engine.memory.slot_state("sarah", "wears", "S2")
    assert state.expected is not None
    assert state.expected.value == "blue_jacket"  # normalised form of "blue blazer"
    assert state.expected.scene_id == "S1"


def test_graph_links_entity_to_every_scene_it_appears_in(engine: ContinuityEngine):
    engine.ingest_script(script_scene("S1", 1, holds="glass"))
    engine.ingest_script(script_scene("S2", 2, holds="glass"))

    assert engine.graph.scene_ids() == ["S1", "S2"]
    assert "character::sarah" in engine.graph.graph
    assert engine.graph.stats()["entities"] == 1


def test_store_round_trips_facts(config: ProjectConfig):
    store = FactStore(":memory:")
    engine = ContinuityEngine(config=config, store=store)
    engine.ingest_script(script_scene("S1", 1, holds="glass"))

    loaded = store.load_facts("TEST")
    assert loaded
    assert any(f.attribute == "holds" and f.value == "glass" for f in loaded)


def test_store_round_trips_issues(config: ProjectConfig):
    store = FactStore(":memory:")
    engine = ContinuityEngine(config=config, store=store)
    engine.ingest_script(script_scene("S1", 1, held_in_hand="left"))
    engine.ingest_footage(footage_scene("S1", 1, hand="right"))
    engine.analyse("S1")

    assert store.load_issues("TEST"), "issues should persist for team 5"
