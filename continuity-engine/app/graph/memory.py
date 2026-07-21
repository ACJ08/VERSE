"""Semantic production memory.

Sits on top of the graph and answers the one question the reasoning layer keeps
asking: *for this entity attribute in this scene, what did we expect and what
did we observe?*

Expected state is resolved by trust, not by recency — a human correction beats
the script, the script beats footage, footage beats AI inference.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import ProjectConfig
from app.graph.builder import KnowledgeGraph
from app.models.schemas import Fact, SourceType

# Sources treated as statements of intent vs. statements of what was filmed.
EXPECTATION_SOURCES = (SourceType.HUMAN, SourceType.SCRIPT, SourceType.CALL_SHEET)
OBSERVATION_SOURCES = (SourceType.FOOTAGE, SourceType.AI_INFERENCE)


@dataclass
class SlotState:
    """Everything known about one (entity, attribute) pair at one scene."""

    entity_key: str
    attribute: str
    scene_id: str | None
    expected: Fact | None
    observed: Fact | None
    expected_candidates: list[Fact]
    observed_candidates: list[Fact]
    history: list[Fact]

    @property
    def has_conflict_candidates(self) -> bool:
        return self.expected is not None and self.observed is not None


class ProductionMemory:
    """Trust-weighted view over the knowledge graph."""

    def __init__(self, graph: KnowledgeGraph, config: ProjectConfig) -> None:
        self._graph = graph
        self._config = config

    def slot_state(self, entity_key: str, attribute: str, scene_id: str | None) -> SlotState:
        scene_facts = self._graph.facts_for(entity_key, attribute, scene_id)
        history = self._graph.facts_for(entity_key, attribute, scene_id, include_history=True)

        expected_pool = [f for f in scene_facts if f.source.type in EXPECTATION_SOURCES]
        observed_pool = [f for f in scene_facts if f.source.type in OBSERVATION_SOURCES]

        # No expectation in this scene? Carry the last trusted one forward —
        # continuity errors are usually about state persisting across scenes.
        if not expected_pool:
            expected_pool = [
                f
                for f in history
                if f.source.type in EXPECTATION_SOURCES and f.scene_id != scene_id
            ]

        return SlotState(
            entity_key=entity_key,
            attribute=attribute,
            scene_id=scene_id,
            expected=self._most_trusted(expected_pool),
            observed=self._most_trusted(observed_pool),
            expected_candidates=expected_pool,
            observed_candidates=observed_pool,
            history=history,
        )

    def _most_trusted(self, facts: list[Fact]) -> Fact | None:
        """Highest-authority fact, tie-broken by narrative recency."""
        if not facts:
            return None
        return max(
            facts,
            key=lambda f: (f.weight, self._graph.timeline.sequence_of(f.scene_id)),
        )

    def iter_slots(self, scene_id: str | None = None):
        """Yield the SlotState for every attribute touched in `scene_id`."""
        for entity_key, attribute in self._graph.slots(scene_id):
            yield self.slot_state(entity_key, attribute, scene_id)

    def value_changed(self, entity_key: str, attribute: str, scene_id: str) -> tuple[Fact, Fact] | None:
        """Detect a change from the previous known value, for narrative checks.

        Returns (previous, current) when the trusted value differs from the
        nearest earlier one, else None.
        """
        history = self._graph.facts_for(entity_key, attribute, scene_id, include_history=True)
        current = [f for f in history if f.scene_id == scene_id]
        previous = [f for f in history if f.scene_id != scene_id]
        if not current or not previous:
            return None
        latest, earlier = self._most_trusted(current), self._most_trusted(previous)
        if latest is None or earlier is None or latest.value == earlier.value:
            return None
        return earlier, latest
