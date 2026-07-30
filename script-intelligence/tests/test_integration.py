"""
VERSE Integration Tests - Script Intelligence → Continuity Engine Pipeline.

Tests that the analyse-and-ingest endpoint correctly:
1. Accepts a screenplay upload.
2. Runs continuity analysis (mocked Granite).
3. Calls forward_scenes_to_engine to push results to the continuity engine (mocked HTTP).
4. Returns the AnalyseScriptResponse.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# ─── Helpers ──────────────────────────────────────────────────────────────────

SCREENPLAY_BYTES = b"""\
INT. KITCHEN - NIGHT

Sarah (30s, blue jacket) stands at the kitchen counter.
She holds a coffee mug in her right hand.

SARAH
I can't believe this is happening.

EXT. ALLEYWAY - NIGHT

John runs down the rain-slicked alleyway.
"""


# ─── Scene Continuity → Engine Payload conversion ─────────────────────────────

def test_scene_continuity_to_engine_payload():
    """bridge._scene_continuity_to_engine_payload converts SceneContinuity correctly."""
    from app.services.ingest_bridge import _scene_continuity_to_engine_payload
    from app.schemas.continuity import (
        SceneContinuity, SceneMetadata, Character, Prop, Lighting, ContinuityNote
    )

    scenes = [
        SceneContinuity(
            metadata=SceneMetadata(
                scene_id="SCENE_001",
                heading="INT. KITCHEN - NIGHT",
                location="KITCHEN",
                time="NIGHT",
                interior_exterior="INT.",
            ),
            characters=[
                Character(name="SARAH", costume="blue jacket", position="at counter", movement=None, emotional_state=None),
            ],
            props=[
                Prop(name="coffee mug", hand_usage="right", state=None, owner="SARAH"),
            ],
            lighting=Lighting(description="dim", source="practical", mood="tense", time_of_day="NIGHT"),
            continuity_notes=[
                ContinuityNote(note="Jacket colour unclear", severity="LOW", category="WARDROBE"),
            ],
            confidence_score=0.95,
        )
    ]

    payload = _scene_continuity_to_engine_payload(scenes, "test-project")

    assert payload["project_id"] == "test-project"
    assert payload["source"] == "script"
    assert len(payload["scenes"]) == 1

    sc = payload["scenes"][0]
    assert sc["scene_id"] == "SCENE_001"
    assert sc["time_of_day"] == "NIGHT"
    assert len(sc["characters"]) == 1
    assert sc["characters"][0]["name"] == "SARAH"
    assert sc["characters"][0]["costume"] == "blue jacket"
    assert len(sc["props"]) == 1
    assert sc["props"][0]["name"] == "coffee mug"
    assert sc["props"][0]["hand_usage"] == "right"
    assert sc["lighting"]["mood"] == "tense"


def test_forward_scenes_no_scenes_returns_none():
    """forward_scenes_to_engine returns None immediately when scenes list is empty."""
    from app.services.ingest_bridge import forward_scenes_to_engine
    result = forward_scenes_to_engine([], "test-project")
    assert result is None


@patch("app.services.ingest_bridge.httpx")
def test_forward_scenes_handles_connection_error(mock_httpx):
    """forward_scenes_to_engine returns None and logs warning on connection failure."""
    from app.services.ingest_bridge import forward_scenes_to_engine
    from app.schemas.continuity import SceneContinuity, SceneMetadata

    # Make httpx.Client raise a connection error
    mock_httpx.Client.return_value.__enter__.return_value.post.side_effect = ConnectionError("unreachable")

    scenes = [
        SceneContinuity(
            metadata=SceneMetadata(scene_id="SCENE_001"),
            confidence_score=1.0,
        )
    ]
    # Should not raise — failure is silently swallowed and None returned
    result = forward_scenes_to_engine(scenes, "test-project")
    assert result is None


# ─── Analyse-and-ingest endpoint ──────────────────────────────────────────────

@patch("app.api.v1.scripts.forward_scenes_to_engine")
@patch("app.api.v1.scripts.ContinuityService.analyse_script_pipeline")
def test_analyse_and_ingest_calls_bridge(mock_analyse, mock_bridge, client: TestClient):
    """POST /api/v1/analyse-and-ingest invokes forward_scenes_to_engine after analysis."""
    from app.schemas.continuity import SceneContinuity, SceneMetadata
    from app.schemas.responses import AnalyseScriptResponse

    mock_scene = SceneContinuity(
        metadata=SceneMetadata(scene_id="SCENE_001"),
        confidence_score=0.9,
    )
    mock_analyse.return_value = AnalyseScriptResponse(
        filename="test.txt",
        scene_count=1,
        scenes=[mock_scene],
        errors=[],
    )
    mock_bridge.return_value = {"facts_ingested": 3, "stats": {}}

    files = {"file": ("test.txt", SCREENPLAY_BYTES, "text/plain")}
    data = {"project_id": "test-project-123"}

    response = client.post("/api/v1/analyse-and-ingest", files=files, data=data)

    assert response.status_code == 200
    result = response.json()
    assert result["scene_count"] == 1
    assert result["filename"] == "test.txt"

    # Bridge must have been called with the scenes and correct project_id
    mock_bridge.assert_called_once()
    call_args = mock_bridge.call_args
    assert call_args[0][1] == "test-project-123"


@patch("app.api.v1.scripts.forward_scenes_to_engine")
@patch("app.api.v1.scripts.ContinuityService.analyse_script_pipeline")
def test_analyse_and_ingest_bridge_failure_does_not_break_response(mock_analyse, mock_bridge, client: TestClient):
    """Bridge failures must not prevent the endpoint from returning the analysis result."""
    from app.schemas.continuity import SceneContinuity, SceneMetadata
    from app.schemas.responses import AnalyseScriptResponse

    mock_scene = SceneContinuity(
        metadata=SceneMetadata(scene_id="SCENE_001"),
        confidence_score=0.9,
    )
    mock_analyse.return_value = AnalyseScriptResponse(
        filename="test.txt",
        scene_count=1,
        scenes=[mock_scene],
        errors=[],
    )
    mock_bridge.return_value = None  # Simulate engine unreachable

    files = {"file": ("test.txt", SCREENPLAY_BYTES, "text/plain")}
    data = {"project_id": "VERSE_DEMO"}

    response = client.post("/api/v1/analyse-and-ingest", files=files, data=data)
    assert response.status_code == 200
    assert response.json()["scene_count"] == 1


@patch("app.api.v1.scripts.forward_scenes_to_engine")
@patch("app.api.v1.scripts.ContinuityService.analyse_script_pipeline")
def test_analyse_and_ingest_default_project_id(mock_analyse, mock_bridge, client: TestClient):
    """When project_id is omitted, defaults to VERSE_DEMO."""
    from app.schemas.continuity import SceneContinuity, SceneMetadata
    from app.schemas.responses import AnalyseScriptResponse

    mock_scene = SceneContinuity(metadata=SceneMetadata(scene_id="SCENE_001"), confidence_score=1.0)
    mock_analyse.return_value = AnalyseScriptResponse(filename="s.txt", scene_count=1, scenes=[mock_scene], errors=[])
    mock_bridge.return_value = None

    files = {"file": ("s.txt", SCREENPLAY_BYTES, "text/plain")}

    response = client.post("/api/v1/analyse-and-ingest", files=files)
    assert response.status_code == 200

    call_args = mock_bridge.call_args
    assert call_args[0][1] == "VERSE_DEMO"
