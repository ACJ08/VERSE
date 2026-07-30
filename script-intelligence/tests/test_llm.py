"""
VERSE Test Suite - Granite / Ollama Integration & Retry Tests.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.llm.granite_client import GraniteClient
from app.llm.retry import retry_with_backoff
from app.schemas.continuity import SceneContinuity
from app.core.errors import InferenceError, ValidationError


def test_extract_json_block_raw():
    raw_text = '```json\n{"characters": [{"name": "SARAH"}]}\n```'
    parsed = GraniteClient._extract_json_block(raw_text)
    assert parsed["characters"][0]["name"] == "SARAH"


def test_extract_json_block_repaired():
    # Trailing comma inside JSON object
    raw_text = '{"characters": [{"name": "SARAH",}],}'
    parsed = GraniteClient._extract_json_block(raw_text)
    assert parsed["characters"][0]["name"] == "SARAH"


def test_extract_json_block_invalid():
    raw_text = "No JSON object here at all."
    with pytest.raises(ValidationError):
        GraniteClient._extract_json_block(raw_text)


def test_retry_with_backoff():
    mock_func = MagicMock(side_effect=[ValueError("Error 1"), ValueError("Error 2"), "Success"])
    decorated = retry_with_backoff(retries=3, backoff_factor=0.01, exceptions=(ValueError,))(mock_func)
    
    result = decorated()
    assert result == "Success"
    assert mock_func.call_count == 3


@patch("app.llm.granite_client.OpenAI")
def test_analyse_scene_mocked(mock_openai):
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"characters": [{"name": "SARAH", "costume": "coat"}], "props": [{"name": "Mug", "hand_usage": "right"}]}'))
    ]
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    client = GraniteClient(base_url="http://mock-server:8000/v1", model="test-granite")
    scene_text = "INT. KITCHEN - NIGHT\nSarah pours coffee."
    
    result = client.analyse_scene(scene_text, scene_id="SCENE_001")
    assert isinstance(result, SceneContinuity)
    assert result.metadata.scene_id == "SCENE_001"
    assert len(result.characters) == 1
    assert result.characters[0].name == "SARAH"
    assert len(result.props) == 1
    assert result.props[0].name == "Mug"
