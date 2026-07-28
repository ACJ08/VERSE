"""
VERSE Test Suite - FastAPI Endpoints Integration Tests.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "granite_configured" in data


def test_upload_script_endpoint(client: TestClient):
    files = {"file": ("test_script.txt", b"INT. KITCHEN - NIGHT\nSarah pours coffee.", "text/plain")}
    response = client.post("/api/v1/upload-script", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_script.txt"
    assert "path" in data


def test_parse_script_endpoint(client: TestClient):
    files = {"file": ("screenplay.txt", b"INT. KITCHEN - NIGHT\nSarah pours coffee.\n\nEXT. GARDEN - DAY\nJohn walks.", "text/plain")}
    response = client.post("/api/v1/parse-script", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["scene_count"] == 2
    assert "extracted_text_path" in data


@patch("app.api.v1.scenes.is_granite_configured", return_value=True)
@patch("app.api.v1.scenes.granite_analyse_scene")
def test_analyse_scene_endpoint(mock_analyse, mock_configured, client: TestClient):
    mock_analyse.return_value = {
        "metadata": {"scene_id": "SCENE_001", "heading": "INT. KITCHEN - NIGHT"},
        "characters": [{"name": "SARAH"}],
        "props": [],
        "lighting": None,
        "continuity_notes": [],
    }

    payload = {"scene_text": "INT. KITCHEN - NIGHT\nSarah enters.", "scene_id": "SCENE_001"}
    response = client.post("/api/v1/analyse-scene", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["scene_id"] == "SCENE_001"
    assert data["characters"][0]["name"] == "SARAH"


def test_parse_call_sheet_endpoint(client: TestClient, sample_call_sheet_text):
    files = {"file": ("call_sheet.txt", sample_call_sheet_text.encode("utf-8"), "text/plain")}
    response = client.post("/api/v1/parse-call-sheet", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "call_sheet.txt"
    assert data["call_sheet"]["production"] == "VERSE Season 1"


def test_legacy_upload_script_endpoint(client: TestClient):
    files = {"file": ("legacy.txt", b"INT. KITCHEN - NIGHT\nSarah enters.", "text/plain")}
    response = client.post("/upload-script", files=files)
    assert response.status_code == 200
    assert response.json()["message"] == "Script uploaded successfully."
