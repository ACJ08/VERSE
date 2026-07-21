"""HTTP contract tests — the surface team 5 integrates against."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import router

from .conftest import footage_scene, script_scene


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def project(request) -> str:
    """Unique project id per test — engines are cached per project."""
    return f"TEST_{request.node.name}"


def test_health(client: TestClient):
    response = client.get("/continuity/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_full_ingest_analyse_feedback_flow(client: TestClient, project: str):
    script = client.post(
        "/continuity/ingest/script",
        json={"project_id": project, "payload": script_scene("S1", 1, held_in_hand="left")},
    )
    assert script.status_code == 200
    assert script.json()["facts_ingested"] > 0

    footage = client.post(
        "/continuity/ingest/footage",
        json={"project_id": project, "payload": footage_scene("S1", 1, hand="right")},
    )
    assert footage.status_code == 200

    analysis = client.post("/continuity/analyse", json={"project_id": project, "scene_id": "S1"})
    assert analysis.status_code == 200
    report = analysis.json()

    assert report["project_id"] == project
    assert report["overall_score"] < 100
    assert any(issue["type"] == "hand_mismatch" for issue in report["issues"])

    issue_id = report["issues"][0]["issue_id"]
    feedback = client.post(
        "/continuity/feedback",
        json={"project_id": project, "action": {"issue_id": issue_id, "action": "dismiss"}},
    )
    assert feedback.status_code == 200
    assert feedback.json()["status"] == "dismissed"


def test_report_shape_matches_the_documented_contract(client: TestClient, project: str):
    """Team 4 renders these keys — breaking them breaks the dashboard."""
    client.post(
        "/continuity/ingest/script",
        json={"project_id": project, "payload": script_scene("S1", 1, held_in_hand="left")},
    )
    client.post(
        "/continuity/ingest/footage",
        json={"project_id": project, "payload": footage_scene("S1", 1, hand="right")},
    )
    report = client.post("/continuity/analyse", json={"project_id": project}).json()

    assert {
        "project_id", "overall_score", "category_scores", "issues",
        "temporary_assumptions", "score_summary",
    } <= set(report)

    issue = report["issues"][0]
    assert {
        "issue_id", "category", "type", "severity", "confidence",
        "expected", "observed", "explanation", "suggested_fix", "status",
    } <= set(issue)
    assert {"value", "source", "source_reference"} <= set(issue["expected"])


def test_unknown_source_is_rejected(client: TestClient, project: str):
    response = client.post(
        "/continuity/ingest/not_a_source", json={"project_id": project, "payload": {}}
    )
    assert response.status_code == 422


def test_feedback_on_unknown_issue_returns_404(client: TestClient, project: str):
    response = client.post(
        "/continuity/feedback",
        json={"project_id": project, "action": {"issue_id": "NOPE", "action": "confirm"}},
    )
    assert response.status_code == 404
