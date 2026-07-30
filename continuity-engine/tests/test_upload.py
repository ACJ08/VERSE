"""Upload endpoint tests — file in, facts out.

The upload endpoints are the ones a user actually touches, so the important
guarantees are about degradation: with no script service and no watsonx
credentials a screenplay must still ingest via the heuristic parser and say so,
and footage must be ingestible as JSON without any vision dependency installed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.upload import router
from app.core.dependencies import get_current_user

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

SCREENPLAY = """INT. COFFEE SHOP - DAY

SARAH sits by the window with a glass of water.

SARAH
We should go.

EXT. STREET - NIGHT

SARAH removes her blue blazer. A storm breaks overhead.
"""


@pytest.fixture
def client(monkeypatch) -> TestClient:
    """Upload router with auth stubbed out — auth is covered in test_api.py."""
    monkeypatch.delenv("SCRIPT_SERVICE_URL", raising=False)
    monkeypatch.delenv("VISION_SERVICE_URL", raising=False)
    monkeypatch.delenv("WATSONX_API_KEY", raising=False)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}
    return TestClient(app)


@pytest.fixture
def project(request) -> str:
    return f"UPLOAD_{request.node.name}"


def test_screenplay_falls_back_to_the_heuristic_parser_and_says_so(client, project):
    response = client.post(
        "/upload/screenplay",
        data={"project_id": project},
        files={"file": ("script.txt", SCREENPLAY.encode(), "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["extractor"] == "heuristic"
    assert body["scenes_detected"] == 2
    assert body["facts_ingested"] > 0
    assert any("heuristic" in w for w in body["warnings"])


def test_screenplay_can_analyse_in_the_same_call(client, project):
    response = client.post(
        "/upload/screenplay",
        data={"project_id": project, "analyse": "true"},
        files={"file": ("script.txt", SCREENPLAY.encode(), "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["report"]["project_id"] == project


def test_screenplay_rejects_an_empty_file(client, project):
    response = client.post(
        "/upload/screenplay",
        data={"project_id": project},
        files={"file": ("script.txt", b"", "text/plain")},
    )
    assert response.status_code == 400


def test_screenplay_rejects_a_file_with_no_scene_headings(client, project):
    response = client.post(
        "/upload/screenplay",
        data={"project_id": project},
        files={"file": ("notes.txt", b"just some notes about the film", "text/plain")},
    )
    assert response.status_code == 422


def test_footage_json_ingests_without_any_vision_dependency(client, project):
    vision = (EXAMPLES / "vision_scene_frames.json").read_bytes()
    response = client.post(
        "/upload/footage",
        data={
            "project_id": project,
            "scene_id": "SCENE_001",
            "entity_aliases": json.dumps({"PERSON_1": "SARAH"}),
            "analyse": "true",
        },
        files={"file": ("scene_001.json", vision, "application/json")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["frames_analysed"] == 8
    assert body["facts_ingested"] > 0
    # Analysis ran, so the dashboard gets its rollup in the same response.
    assert body["report"]["project_id"] == project
    assert body["overview"]["scenes_shot"] == 1
    assert body["scenes"][0]["scene_id"] == "SCENE_001"


def test_footage_upload_reports_missing_identity_mapping(client, project):
    vision = (EXAMPLES / "vision_scene_frames.json").read_bytes()
    response = client.post(
        "/upload/footage",
        data={"project_id": project, "scene_id": "SCENE_001"},
        files={"file": ("scene_001.json", vision, "application/json")},
    )
    assert response.status_code == 200
    assert any("PERSON_n" in w for w in response.json()["warnings"])


def test_footage_upload_rejects_malformed_json(client, project):
    response = client.post(
        "/upload/footage",
        data={"project_id": project},
        files={"file": ("scene_001.json", b"{not json", "application/json")},
    )
    assert response.status_code == 422


def test_footage_upload_rejects_malformed_aliases(client, project):
    vision = (EXAMPLES / "vision_scene_frames.json").read_bytes()
    response = client.post(
        "/upload/footage",
        data={"project_id": project, "entity_aliases": "PERSON_1=SARAH"},
        files={"file": ("scene_001.json", vision, "application/json")},
    )
    assert response.status_code == 422


def test_video_upload_without_a_vision_service_is_a_clear_503(client, project):
    response = client.post(
        "/upload/footage",
        data={"project_id": project, "scene_id": "SCENE_001"},
        files={"file": ("clip.mp4", b"\x00\x00\x00 ftypmp42", "video/mp4")},
    )
    assert response.status_code == 503
    assert "VISION_SERVICE_URL" in response.json()["detail"]


def test_call_sheet_upload_without_the_script_service_is_a_clear_503(client, project):
    response = client.post(
        "/upload/call-sheet",
        data={"project_id": project},
        files={"file": ("day12.pdf", b"%PDF-1.4 call sheet", "application/pdf")},
    )
    assert response.status_code == 503
    assert "SCRIPT_SERVICE_URL" in response.json()["detail"]


def test_screenplay_prefers_the_script_service_when_configured(client, project, monkeypatch):
    """With the service up, its richer extraction is used instead of regex."""
    from app.services import pipeline

    response_payload = json.loads(
        (EXAMPLES / "script_intelligence_response.json").read_text(encoding="utf-8")
    )

    def fake_analyse(self, filename, data):  # noqa: ANN001 - test double
        return response_payload

    monkeypatch.setenv("SCRIPT_SERVICE_URL", "http://script-service.test")
    monkeypatch.setattr(pipeline.ScriptServiceClient, "analyse_script", fake_analyse)

    result = client.post(
        "/upload/screenplay",
        data={"project_id": project},
        files={"file": ("script.txt", SCREENPLAY.encode(), "text/plain")},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["extractor"] == "script-intelligence/granite"
    assert body["scene_ids"] == ["SCENE_001", "SCENE_002", "SCENE_003"]
    assert body["notes"], "the script service's continuity notes should be surfaced"


def test_screenplay_falls_back_when_the_script_service_is_down(client, project, monkeypatch):
    from app.services import pipeline

    def fail(self, filename, data):  # noqa: ANN001 - test double
        raise pipeline.UpstreamUnavailable("Script Intelligence service at x is unavailable: boom")

    monkeypatch.setenv("SCRIPT_SERVICE_URL", "http://script-service.test")
    monkeypatch.setattr(pipeline.ScriptServiceClient, "analyse_script", fail)

    result = client.post(
        "/upload/screenplay",
        data={"project_id": project},
        files={"file": ("script.txt", SCREENPLAY.encode(), "text/plain")},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["extractor"] == "heuristic"
    assert any("unavailable" in w for w in body["warnings"])
