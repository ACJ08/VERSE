"""Timeline-based knowledge graph.

NetworkX holds the live graph; `storage.py` persists it. Conflicting facts are
kept side by side on the same (entity, attribute, scene) slot — resolution
happens in the reasoning layer, never here.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import networkx as nx

from app.config import ProjectConfig
from app.graph.timeline import Timeline
from app.ingestion.entity_matcher import EntityMatcher
from app.models.schemas import EntityRef, EntityType, Fact, SourceType

# Relationship labels used on graph edges.
REL_APPEARS_IN = "APPEARS_IN"
REL_HAS_ATTRIBUTE = "HAS_ATTRIBUTE"
REL_BEFORE = "BEFORE"
REL_SUPPORTED_BY = "SUPPORTED_BY"


class KnowledgeGraph:
    """Entity/scene graph plus a fact index for fast comparison lookups.

    The graph answers structural questions ("what appears in scene 12?"); the
    fact index answers attribute questions ("what did each source say about
    Sarah's hand in scene 12?").
    """

    def __init__(self, config: ProjectConfig, matcher: EntityMatcher | None = None) -> None:
        self._config = config
        self._matcher = matcher or EntityMatcher(config)
        self.graph = nx.MultiDiGraph()
        self.timeline = Timeline()
        # (entity_key, attribute) -> scene_id -> facts
        self._facts: dict[tuple[str, str], dict[str | None, list[Fact]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._by_id: dict[str, Fact] = {}

    # -- ingestion ---------------------------------------------------------- #

    def add_facts(self, facts: Iterable[Fact]) -> list[Fact]:
        """Add facts, resolving entity aliases and extending the timeline.

        Returns the stored facts with their canonical entity attached, so the
        caller sees exactly what went into the graph.
        """
        stored: list[Fact] = []
        for fact in facts:
            canonical = self._matcher.resolve(fact.entity)
            resolved = fact.model_copy(update={"entity": canonical})
            self._register(resolved)
            stored.append(resolved)

        self._link_timeline()
        return stored

    def _register(self, fact: Fact) -> None:
        entity = fact.entity
        entity_node = _entity_node(entity)

        if entity_node not in self.graph:
            self.graph.add_node(
                entity_node,
                kind="entity",
                entity_type=entity.type.value,
                name=entity.name,
                raw_type=entity.raw_type,
            )

        if fact.scene_id:
            scene_node = _scene_node(fact.scene_id)
            self.timeline.add(fact.scene_id, fact.sequence)
            if scene_node not in self.graph:
                self.graph.add_node(
                    scene_node,
                    kind="scene",
                    scene_id=fact.scene_id,
                    sequence=self.timeline.sequence_of(fact.scene_id),
                )
            if not self.graph.has_edge(entity_node, scene_node, key=REL_APPEARS_IN):
                self.graph.add_edge(entity_node, scene_node, key=REL_APPEARS_IN)

        self.graph.add_edge(
            entity_node,
            f"attr::{entity.key}::{fact.attribute}",
            key=REL_HAS_ATTRIBUTE,
            fact_id=fact.fact_id,
            value=fact.value,
            source=fact.source.type.value,
            scene_id=fact.scene_id,
            confidence=fact.confidence,
        )

        self._facts[(entity.key, fact.attribute)][fact.scene_id].append(fact)
        self._by_id[fact.fact_id] = fact

    def _link_timeline(self) -> None:
        """Rebuild BEFORE edges so scene order stays correct as data arrives."""
        ordered = self.timeline.ordered()
        for previous, current in zip(ordered, ordered[1:]):
            a, b = _scene_node(previous.scene_id), _scene_node(current.scene_id)
            if a in self.graph and b in self.graph and not self.graph.has_edge(a, b, key=REL_BEFORE):
                self.graph.add_edge(a, b, key=REL_BEFORE)

    # -- queries ------------------------------------------------------------ #

    def facts_for(
        self,
        entity_key: str,
        attribute: str,
        scene_id: str | None = None,
        include_history: bool = False,
    ) -> list[Fact]:
        """Facts for an entity attribute, optionally including earlier scenes.

        With `include_history`, results are ordered by narrative proximity to
        `scene_id` so nearby evidence is considered first.
        """
        buckets = self._facts.get((entity_key, attribute), {})
        if scene_id is not None and not include_history:
            return list(buckets.get(scene_id, []))

        collected = [f for facts in buckets.values() for f in facts]
        if scene_id is None:
            return collected
        target = self.timeline.sequence_of(scene_id)
        relevant = [f for f in collected if self.timeline.sequence_of(f.scene_id) <= target]
        relevant.sort(key=lambda f: self.timeline.proximity(scene_id, f.scene_id), reverse=True)
        return relevant

    def slots(self, scene_id: str | None = None) -> list[tuple[str, str]]:
        """All (entity_key, attribute) pairs, optionally limited to one scene."""
        if scene_id is None:
            return list(self._facts.keys())
        return [key for key, buckets in self._facts.items() if scene_id in buckets]

    def scene_ids(self) -> list[str]:
        return [node.scene_id for node in self.timeline.ordered()]

    def entity(self, entity_key: str) -> EntityRef | None:
        return self._matcher.entities.get(entity_key)

    def fact(self, fact_id: str) -> Fact | None:
        return self._by_id.get(fact_id)

    def all_facts(self) -> list[Fact]:
        return list(self._by_id.values())

    def facts_by_source(self, source: SourceType) -> list[Fact]:
        return [f for f in self._by_id.values() if f.source.type is source]

    def replace_fact(self, fact: Fact) -> None:
        """Swap a stored fact for an edited version, preserving its slot.

        Used by the feedback layer when a human corrects a value.
        """
        existing = self._by_id.get(fact.fact_id)
        if existing is None:
            self._register(fact)
            return
        bucket = self._facts[(existing.entity.key, existing.attribute)][existing.scene_id]
        for index, candidate in enumerate(bucket):
            if candidate.fact_id == fact.fact_id:
                bucket[index] = fact
                break
        self._by_id[fact.fact_id] = fact

    # -- introspection ------------------------------------------------------ #

    def stats(self) -> dict[str, int]:
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "facts": len(self._by_id),
            "scenes": len(self.timeline),
            "entities": len(self._matcher.entities),
        }


def _entity_node(entity: EntityRef) -> str:
    kind = entity.type.value if entity.type is not EntityType.CUSTOM else "custom"
    return f"{kind}::{entity.key}"


def _scene_node(scene_id: str) -> str:
    return f"scene::{scene_id}"
