"""HTTP tests for the ingestion pipeline surface.

Covers what the frontend calls: posting a producing team's native payload,
running script + footage together, and reading the scene and entity views. Also
pins the two behaviours that are easy to regress — duplicate payloads must not
double-count facts, and an offline upstream service must degrade rather than 500.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import router
from app.services.pipeline import ScriptServiceClient, UpstreamUnavailable, VisionServiceClient

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def project(request) -> str:
    """Unique project id per test — engines are cached per project."""
    return f"PIPE_{request.node.name}"


@pytest.fixture
def script_response() -> dict[str, Any]:
    return json.loads((EXAMPLES / "script_intelligence_response.json").read_text(encoding="utf-8"))


@pytest.fixture
def vision_frames() -> dict[str, Any]:
    return json.loads((EXAMPLES / "vision_scene_frames.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# ingest-adapted
# --------------------------------------------------------------------------- #


def test_ingest_script_intelligence_shape(client: TestClient, project: str, script_response):
    response = client.post(
        "/continuity/ingest-adapted/script",
        json={"project_id": project, "payload": script_response},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["facts_ingested"] > 0
    assert body["scene_ids"] == ["SCENE_001", "SCENE_002", "SCENE_003"]
    assert body["extractor"] == "granite"
    # The script model's own notes are reported, never ingested as facts.
    assert body["notes"][0]["scene_id"] == "SCENE_001"


def test_ingest_vision_shape_aggregates_frames(client: TestClient, project: str, vision_frames):
    response = client.post(
        "/continuity/ingest-adapted/footage",
        json={
            "project_id": project,
            "payload": vision_frames,
            "entity_aliases": {"PERSON_1": "SARAH"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["frames_analysed"] == 8
    assert body["source"] == "footage"
    assert "character:SARAH" in body["entities"]


def test_ingest_auto_detects_the_shape(client: TestClient, project: str, vision_frames):
    response = client.post(
        "/continuity/ingest-adapted/auto",
        json={"project_id": project, "payload": vision_frames},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "footage"


def test_ingest_adapted_rejects_an_unknown_shape(client: TestClient, project: str):
    response = client.post(
        "/continuity/ingest-adapted/nonsense", json={"project_id": project, "payload": {}}
    )
    assert response.status_code == 422


def test_duplicate_payloads_do_not_double_count(client: TestClient, project: str, vision_frames):
    body = {"project_id": project, "payload": vision_frames}
    first = client.post("/continuity/ingest-adapted/footage", json=body).json()
    second = client.post("/continuity/ingest-adapted/footage", json=body).json()
    assert first["facts_ingested"] > 0
    assert second["facts_ingested"] == 0
    assert second["duplicate"] is True
    assert first["graph_stats"]["facts"] == second["graph_stats"]["facts"]


def test_ingest_can_analyse_in_the_same_call(client: TestClient, project: str, script_response):
    response = client.post(
        "/continuity/ingest-adapted/script",
        json={"project_id": project, "payload": script_response, "analyse": True},
    )
    assert response.status_code == 200
    assert "report" in response.json()


# --------------------------------------------------------------------------- #
# pipeline/run
# --------------------------------------------------------------------------- #


def test_pipeline_run_ingests_both_sides_and_reports(
    client: TestClient, project: str, script_response, vision_frames
):
    response = client.post(
        "/continuity/pipeline/run",
        json={
            "project_id": project,
            "script": script_response,
            "footage": vision_frames,
            "entity_aliases": {"PERSON_1": "SARAH"},
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert [step["source"] for step in body["steps"]] == ["script", "footage"]
    assert all(step["facts_ingested"] > 0 for step in body["steps"])

    # Script-only scenes are present and marked unshot; the shot one is compared.
    scenes = {s["scene_id"]: s for s in body["scenes"]}
    assert scenes["SCENE_001"]["has_footage"] is True
    assert scenes["SCENE_003"]["has_footage"] is False
    assert body["overview"]["scenes_total"] == 3
    assert body["overview"]["scenes_shot"] == 1
    assert 0 <= body["report"]["overall_score"] <= 100


def test_pipeline_run_needs_at_least_one_payload(client: TestClient, project: str):
    response = client.post("/continuity/pipeline/run", json={"project_id": project})
    assert response.status_code == 422


def test_pipeline_run_ingests_a_call_sheet_as_call_sheet_source(client: TestClient, project: str):
    response = client.post(
        "/continuity/pipeline/run",
        json={
            "project_id": project,
            "call_sheet": {
                "call_sheet": {
                    "location": "STAGE 4",
                    "scenes": ["1"],
                    "cast": ["SARAH - 07:00"],
                    "shooting_time": "06:30",
                }
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["steps"][0]["source"] == "call_sheet"


# --------------------------------------------------------------------------- #
# Read models
# --------------------------------------------------------------------------- #


def test_scenes_endpoint_returns_rollup_and_overview(
    client: TestClient, project: str, script_response, vision_frames
):
    client.post(
        "/continuity/pipeline/run",
        json={
            "project_id": project,
            "script": script_response,
            "footage": vision_frames,
            "entity_aliases": {"PERSON_1": "SARAH"},
        },
    )
    response = client.get(f"/continuity/scenes/{project}")
    assert response.status_code == 200
    body = response.json()
    assert [s["scene_id"] for s in body["scenes"]] == ["SCENE_001", "SCENE_002", "SCENE_003"]
    assert body["overview"]["scenes_total"] == 3
    assert body["scenes"][0]["headline"]


def test_entities_endpoint_filters_for_the_costume_screen(
    client: TestClient, project: str, script_response, vision_frames
):
    client.post(
        "/continuity/pipeline/run",
        json={
            "project_id": project,
            "script": script_response,
            "footage": vision_frames,
            "entity_aliases": {"PERSON_1": "SARAH"},
        },
    )
    response = client.get(
        f"/continuity/entities/{project}",
        params={"entity_type": "character", "attribute": "wears"},
    )
    assert response.status_code == 200
    views = response.json()
    assert views
    assert all(v["entity"]["type"] == "character" for v in views)
    assert all(slot["attribute"] == "wears" for v in views for slot in v["slots"])

    sarah = next(v for v in views if v["entity"]["key"] == "sarah")
    scene_one = next(s for s in sarah["slots"] if s["scene_id"] == "SCENE_001")
    assert scene_one["expected"]["source"] == "script"
    assert scene_one["observed"]["source"] == "footage"


def test_entities_endpoint_accepts_comma_separated_filters(
    client: TestClient, project: str, script_response
):
    client.post(
        "/continuity/ingest-adapted/script",
        json={"project_id": project, "payload": script_response},
    )
    response = client.get(
        f"/continuity/entities/{project}", params={"entity_type": "character,prop"}
    )
    assert response.status_code == 200
    assert {v["entity"]["type"] for v in response.json()} == {"character", "prop"}


def test_scenes_endpoint_is_empty_for_an_unknown_project(client: TestClient):
    response = client.get("/continuity/scenes/NEVER_SEEN")
    assert response.status_code == 200
    assert response.json()["scenes"] == []


# --------------------------------------------------------------------------- #
# Upstream clients
# --------------------------------------------------------------------------- #


def test_upstream_clients_are_unconfigured_without_env(monkeypatch):
    monkeypatch.delenv("SCRIPT_SERVICE_URL", raising=False)
    monkeypatch.delenv("VISION_SERVICE_URL", raising=False)
    assert ScriptServiceClient().is_configured is False
    assert VisionServiceClient().is_configured is False


def test_unconfigured_upstream_raises_the_fallback_signal(monkeypatch):
    """`UpstreamUnavailable` is what makes the upload endpoint fall back."""
    monkeypatch.delenv("SCRIPT_SERVICE_URL", raising=False)
    with pytest.raises(UpstreamUnavailable):
        ScriptServiceClient().analyse_script("script.txt", b"INT. ROOM - DAY")


def test_unreachable_upstream_raises_rather_than_propagating_http_errors(monkeypatch):
    monkeypatch.setenv("SCRIPT_SERVICE_URL", "http://127.0.0.1:9")  # discard port
    with pytest.raises(UpstreamUnavailable):
        ScriptServiceClient(timeout=1.0).analyse_script("script.txt", b"INT. ROOM - DAY")
