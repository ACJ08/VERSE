"""Integration tests — Granite fact extractor wiring inside ContinuityEngine.

Verifies that:
1. _build_granite_extractor() returns None gracefully when the Granite server
   is not reachable (import/connection failure).
2. When _granite_extractor is None the engine still ingests all DynamicParser facts
   without any error.
3. When _granite_extractor is set (mocked), _extract_granite_facts is called for
   scenes that contain an "action" field, and the extra facts are merged in.
4. Duplicate facts from Granite (same entity/attribute/scene) are not added twice.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from app.config import ProjectConfig
from app.engine import ContinuityEngine
from app.models.schemas import EntityRef, EntityType, Fact, SourceRef, SourceType


def _make_fact(entity_name: str, attribute: str, scene_id: str | None = None) -> Fact:
    return Fact(
        fact_id=f"FACT_{entity_name}_{attribute}",
        entity=EntityRef(type=EntityType.CHARACTER, name=entity_name),
        attribute=attribute,
        value="test_value",
        scene_id=scene_id,
        source=SourceRef(type=SourceType.AI_INFERENCE, extractor="ibm-granite"),
        confidence=0.9,
    )


# ─── Graceful degradation ─────────────────────────────────────────────────────

def test_build_granite_extractor_returns_none_when_unavailable():
    """Engine must not raise when the Granite/Ollama server import fails."""
    with patch("app.engine.GraniteFactExtractor", side_effect=ImportError("no requests")):
        config = ProjectConfig.from_dict({"project_id": "TEST_GE_1"})
        engine = ContinuityEngine(config=config)
    assert engine._granite_extractor is None


def test_ingest_without_granite_extractor_works(engine):
    """DynamicParser facts are still ingested when _granite_extractor is None."""
    engine._granite_extractor = None  # Ensure extractor is off
    payload = {
        "scenes": [
            {
                "scene_id": "S1",
                "sequence": 1,
                "characters": [{"name": "Elena", "type": "character", "costume": "navy jacket"}],
            }
        ]
    }
    facts = engine.ingest_script(payload, extractor="granite")
    assert len(facts) > 0
    assert any(f.entity.name.lower() == "elena" for f in facts)


# ─── Granite augmentation ─────────────────────────────────────────────────────

def test_granite_facts_are_merged_when_extractor_present(engine):
    """Extra Granite facts are appended to the DynamicParser facts."""
    granite_fact = _make_fact("SARAH", "lighting_state", "S1")
    mock_extractor = MagicMock()
    mock_extractor.extract_scene_facts.return_value = [granite_fact]

    engine._granite_extractor = mock_extractor

    payload = {
        "scenes": [
            {
                "scene_id": "S1",
                "sequence": 1,
                "action": "Sarah enters the darkened kitchen.",
                "characters": [{"name": "Sarah", "type": "character", "costume": "blue dress"}],
            }
        ]
    }
    facts = engine.ingest_script(payload, extractor="granite")

    # Extractor must have been called once for the scene with action text
    mock_extractor.extract_scene_facts.assert_called_once()
    call_kwargs = mock_extractor.extract_scene_facts.call_args[1]
    assert "darkened kitchen" in call_kwargs.get("scene_text", "")

    # The Granite-supplied fact should appear in the stored facts
    fact_attributes = {(f.entity.key, f.attribute) for f in facts}
    assert ("sarah", "lighting_state") in fact_attributes


def test_granite_facts_not_duplicated(engine):
    """If Granite returns a fact with the same (entity, attribute, scene) as the parser,
    it must NOT be added twice."""
    # The DynamicParser will emit a "costume" fact for Elena.
    # We make Granite return the same fact signature.
    duplicate_granite_fact = _make_fact("ELENA", "costume", "S1")
    mock_extractor = MagicMock()
    mock_extractor.extract_scene_facts.return_value = [duplicate_granite_fact]

    engine._granite_extractor = mock_extractor

    payload = {
        "scenes": [
            {
                "scene_id": "S1",
                "sequence": 1,
                "action": "Elena enters.",
                "characters": [{"name": "Elena", "type": "character", "costume": "navy jacket"}],
            }
        ]
    }
    facts = engine.ingest_script(payload, extractor="granite")

    # Count facts with (elena, costume, S1)
    matching = [
        f for f in facts
        if f.entity.key == "elena" and f.attribute in ("costume", "wardrobe") and f.scene_id == "S1"
    ]
    assert len(matching) == 1, "Duplicate granite fact must not be added twice"


def test_granite_extractor_failure_is_silenced(engine):
    """If the Granite client raises during fact extraction, ingestion must still succeed."""
    mock_extractor = MagicMock()
    mock_extractor.extract_scene_facts.side_effect = ConnectionError("Ollama down")

    engine._granite_extractor = mock_extractor

    payload = {
        "scenes": [
            {
                "scene_id": "S1",
                "sequence": 1,
                "action": "Sarah pours coffee.",
                "characters": [{"name": "Sarah", "type": "character"}],
            }
        ]
    }
    # Must not raise — Granite failure is silently ignored
    facts = engine.ingest_script(payload, extractor="granite")
    assert len(facts) > 0


def test_no_granite_call_without_action_field(engine):
    """Granite extractor is NOT called for scenes lacking an 'action' field."""
    mock_extractor = MagicMock()
    mock_extractor.extract_scene_facts.return_value = []
    engine._granite_extractor = mock_extractor

    payload = {
        "scenes": [
            {
                "scene_id": "S1",
                "sequence": 1,
                # No "action" key — nothing to send to Granite
                "characters": [{"name": "Sarah", "type": "character"}],
            }
        ]
    }
    engine.ingest_script(payload, extractor="granite")
    mock_extractor.extract_scene_facts.assert_not_called()
