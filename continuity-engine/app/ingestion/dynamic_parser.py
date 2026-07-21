"""Dynamic JSON -> Fact conversion.

The engine must not depend on fixed field names. The parser walks arbitrary
nested JSON, works out which object is an entity, and emits one Fact per leaf
attribute. Unknown fields become facts with `EntityType.CUSTOM` rather than
being dropped.

Recognised-but-optional envelope keys (any casing, any nesting depth):
    scenes[] / scene_id / id        -> scene grouping
    sequence / order / scene_number -> screenplay order
    timestamp / time / at           -> footage time
    confidence / score              -> per-observation confidence
    source / origin                 -> overrides the caller's default source
"""

from __future__ import annotations

import uuid
from typing import Any, Iterable

from app.config import ProjectConfig
from app.ingestion.normaliser import Normaliser
from app.models.schemas import (
    EntityRef,
    EntityType,
    Fact,
    SourceRef,
    SourceType,
    normalise_key,
)

# Keys consumed as metadata rather than emitted as facts.
_SCENE_KEYS = {"scene_id", "scene", "sceneid", "scene_number", "scene_no"}
_SEQUENCE_KEYS = {"sequence", "order", "index", "scene_number", "scene_no"}
_TIME_KEYS = {"timestamp", "time", "at", "start_time", "frame_time"}
_CONFIDENCE_KEYS = {"confidence", "confidence_score", "score", "certainty"}
_NAME_KEYS = {"name", "id", "label", "character", "character_name", "title"}
_SOURCE_KEYS = {"source", "origin", "source_type"}
_REFERENCE_KEYS = {"source_reference", "reference", "ref", "citation"}
_ENTITY_LIST_KEYS = {
    "characters", "props", "costumes", "objects", "items", "wardrobe",
    "locations", "actions", "entities", "detections", "observations",
}
_SKIP_KEYS = _SCENE_KEYS | _SEQUENCE_KEYS | _TIME_KEYS | _CONFIDENCE_KEYS | _SOURCE_KEYS | _REFERENCE_KEYS


class _Context:
    """Metadata inherited down the JSON tree by nested objects."""

    __slots__ = ("scene_id", "sequence", "timestamp", "confidence", "source", "reference")

    def __init__(self) -> None:
        self.scene_id: str | None = None
        self.sequence: int | None = None
        self.timestamp: str | None = None
        self.confidence: float = 1.0
        self.source: SourceType | None = None
        self.reference: str = ""

    def child(self) -> "_Context":
        clone = _Context()
        for slot in self.__slots__:
            setattr(clone, slot, getattr(self, slot))
        return clone


class DynamicParser:
    """Converts producer JSON into normalised Facts.

    Stateless between calls apart from config, so it is safe to share one
    instance across requests.
    """

    def __init__(self, config: ProjectConfig, normaliser: Normaliser | None = None) -> None:
        self._config = config
        self._normaliser = normaliser or Normaliser(config)

    def parse(
        self,
        payload: Any,
        default_source: SourceType,
        extractor: str | None = None,
    ) -> list[Fact]:
        """Parse a script or footage payload into facts.

        `default_source` is what the caller claims (script vs footage); the
        payload may override it per-node via a `source` field.
        """
        context = _Context()
        context.source = default_source
        facts: list[Fact] = []
        self._walk(payload, context, None, facts, extractor)
        return facts

    # -- traversal ---------------------------------------------------------- #

    def _walk(
        self,
        node: Any,
        context: _Context,
        entity: EntityRef | None,
        out: list[Fact],
        extractor: str | None,
        parent_key: str = "",
    ) -> None:
        if isinstance(node, list):
            for item in node:
                self._walk(item, context, entity, out, extractor, parent_key)
            return

        if not isinstance(node, dict):
            # A bare scalar under a key — attribute of the enclosing entity.
            if entity is not None and parent_key:
                out.append(self._make_fact(entity, parent_key, node, context, extractor))
            return

        local = self._absorb_metadata(node, context)
        local_entity = self._resolve_entity(node, entity, parent_key)

        for key, value in node.items():
            if normalise_key(key) in _SKIP_KEYS or normalise_key(key) in _NAME_KEYS:
                continue

            if isinstance(value, (dict, list)):
                self._walk(value, local, local_entity, out, extractor, key)
            elif local_entity is not None:
                out.append(self._make_fact(local_entity, key, value, local, extractor))
            else:
                # Scene-level scalar with no entity yet — attach to the scene.
                scene_entity = EntityRef(
                    type=EntityType.SCENE, name=local.scene_id or "unknown_scene"
                )
                out.append(self._make_fact(scene_entity, key, value, local, extractor))

    # -- helpers ------------------------------------------------------------ #

    def _absorb_metadata(self, node: dict[str, Any], context: _Context) -> _Context:
        """Pull envelope fields off a node and inherit the rest from the parent."""
        local = context.child()
        for key, value in node.items():
            nkey = normalise_key(key)
            if nkey in _SCENE_KEYS and isinstance(value, (str, int)):
                local.scene_id = str(value)
            if nkey in _SEQUENCE_KEYS and isinstance(value, int):
                local.sequence = value
            if nkey in _TIME_KEYS and isinstance(value, (str, int, float)):
                local.timestamp = str(value)
            if nkey in _CONFIDENCE_KEYS and isinstance(value, (int, float)):
                local.confidence = float(value)
            if nkey in _SOURCE_KEYS and isinstance(value, str):
                local.source = _coerce_source(value) or local.source
            if nkey in _REFERENCE_KEYS and isinstance(value, str):
                local.reference = value
        return local

    def _resolve_entity(
        self, node: dict[str, Any], inherited: EntityRef | None, parent_key: str
    ) -> EntityRef | None:
        """Decide whether this dict describes an entity of its own."""
        name = None
        for key, value in node.items():
            if normalise_key(key) in _NAME_KEYS and isinstance(value, str):
                name = value
                break
        if name is None:
            return inherited

        explicit = node.get("type") or node.get("entity_type")
        hint = str(explicit) if explicit else parent_key
        entity_type = self._normaliser.entity_type(hint)
        raw_type = str(explicit) if explicit and entity_type is EntityType.CUSTOM else None
        return EntityRef(type=entity_type, name=name, raw_type=raw_type)

    def _make_fact(
        self,
        entity: EntityRef,
        raw_attribute: str,
        raw_value: Any,
        context: _Context,
        extractor: str | None,
    ) -> Fact:
        source_type = context.source or SourceType.AI_INFERENCE
        attribute = self._normaliser.attribute(raw_attribute)
        return Fact(
            fact_id=f"FACT_{uuid.uuid4().hex[:10]}",
            entity=entity,
            attribute=attribute,
            value=self._normaliser.value(raw_value),
            raw_attribute=raw_attribute,
            raw_value=raw_value,
            scene_id=context.scene_id,
            sequence=context.sequence,
            timestamp=context.timestamp,
            source=SourceRef(
                type=source_type,
                reference=context.reference or _default_reference(context),
                extractor=extractor,
            ),
            confidence=context.confidence,
            trust=self._config.trust(source_type),
            human_confirmed=source_type is SourceType.HUMAN,
        )


def _default_reference(context: _Context) -> str:
    if context.timestamp:
        return context.timestamp
    if context.scene_id:
        return f"Scene {context.scene_id}"
    return ""


def _coerce_source(value: str) -> SourceType | None:
    key = normalise_key(value)
    for source in SourceType:
        if source.value == key or source.value in key:
            return source
    return None


def parse_many(
    parser: DynamicParser, payloads: Iterable[tuple[Any, SourceType, str | None]]
) -> list[Fact]:
    """Convenience for ingesting script + footage + call sheets in one pass."""
    facts: list[Fact] = []
    for payload, source, extractor in payloads:
        facts.extend(parser.parse(payload, source, extractor))
    return facts
