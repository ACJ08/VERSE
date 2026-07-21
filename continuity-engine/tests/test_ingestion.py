"""Ingestion: dynamic parsing, normalisation, entity matching."""

from __future__ import annotations

from app.config import ProjectConfig
from app.ingestion.dynamic_parser import DynamicParser
from app.ingestion.entity_matcher import EntityMatcher
from app.ingestion.normaliser import Normaliser
from app.models.schemas import EntityRef, EntityType, SourceType


def test_parses_nested_payload_into_facts(config: ProjectConfig, script_payload):
    facts = DynamicParser(config).parse(script_payload, SourceType.SCRIPT)

    assert facts, "expected facts from the example script"
    sarah = [f for f in facts if f.entity.name == "Sarah"]
    assert sarah, "Sarah should be recognised as an entity"
    assert all(f.source.type is SourceType.SCRIPT for f in facts)
    assert {f.scene_id for f in sarah} == {"SCENE_011", "SCENE_012", "SCENE_013"}


def test_scene_and_confidence_metadata_are_inherited(config: ProjectConfig, footage_payload):
    facts = DynamicParser(config).parse(footage_payload, SourceType.FOOTAGE)

    scene_12 = [f for f in facts if f.scene_id == "SCENE_012"]
    assert scene_12
    assert all(f.timestamp == "00:14.2" for f in scene_12)
    assert all(f.confidence == 0.91 for f in scene_12)


def test_unknown_field_becomes_a_fact_not_an_error(config: ProjectConfig):
    """Case 11: unknown entity/attribute types are added dynamically."""
    payload = {
        "scenes": [
            {
                "scene_id": "S1",
                "sequence": 1,
                "entities": [
                    {"name": "Rex", "type": "animal", "collar_colour": "red", "mood": "calm"}
                ],
            }
        ]
    }
    facts = DynamicParser(config).parse(payload, SourceType.SCRIPT)

    rex = [f for f in facts if f.entity.name == "Rex"]
    assert {f.attribute for f in rex} >= {"collar_colour", "mood"}
    assert rex[0].entity.type is EntityType.CUSTOM
    assert rex[0].entity.raw_type == "animal"


def test_original_labels_are_preserved(config: ProjectConfig):
    """The UI must be able to show what the producing team actually said."""
    facts = DynamicParser(config).parse(
        {"scenes": [{"scene_id": "S1", "characters": [{"name": "Sarah", "hand": "left"}]}]},
        SourceType.FOOTAGE,
    )
    hand = next(f for f in facts if f.attribute == "held_in_hand")
    assert hand.raw_attribute == "hand", "raw field name must survive normalisation"
    assert hand.raw_value == "left"


def test_attribute_aliases_normalise_to_one_name(config: ProjectConfig):
    normaliser = Normaliser(config)
    assert normaliser.attribute("hand") == "held_in_hand"
    assert normaliser.attribute("hand_position") == "held_in_hand"
    assert normaliser.attribute("wardrobe") == "wears"
    assert normaliser.attribute("position") == "screen_position"


def test_similar_values_are_matched(config: ProjectConfig):
    """Case 12: similar natural-language entities are matched."""
    normaliser = Normaliser(config)
    assert normaliser.values_match("blue blazer", "navy jacket")
    assert normaliser.values_match("left", "left hand")
    assert not normaliser.values_match("left", "right")


def test_entity_matcher_merges_aliases_within_a_type(config: ProjectConfig):
    matcher = EntityMatcher(config)
    first = matcher.resolve(EntityRef(type=EntityType.CHARACTER, name="Sarah"))
    second = matcher.resolve(EntityRef(type=EntityType.CHARACTER, name="SARAH"))

    assert second.key == first.key
    assert len(matcher.entities) == 1


def test_entity_matcher_keeps_types_apart(config: ProjectConfig):
    """A prop named Sarah must never merge into the character Sarah."""
    matcher = EntityMatcher(config)
    matcher.resolve(EntityRef(type=EntityType.CHARACTER, name="Sarah"))
    matcher.resolve(EntityRef(type=EntityType.PROP, name="Sarah"))

    assert len(matcher.entities) == 2
