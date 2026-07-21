"""Shared fixtures and payload builders.

Tests construct payloads through `script_scene` / `footage_scene` rather than
inline dicts so that when teams 1 and 2 change their JSON shape, only these
two helpers need updating.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.config import ProjectConfig
from app.engine import ContinuityEngine

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def config() -> ProjectConfig:
    return ProjectConfig.from_dict({"project_id": "TEST"})


@pytest.fixture
def engine(config: ProjectConfig) -> ContinuityEngine:
    return ContinuityEngine(config=config)


@pytest.fixture
def script_payload() -> dict[str, Any]:
    return json.loads((EXAMPLES / "script_scenes.json").read_text(encoding="utf-8"))


@pytest.fixture
def footage_payload() -> dict[str, Any]:
    return json.loads((EXAMPLES / "footage_observations.json").read_text(encoding="utf-8"))


def script_scene(
    scene_id: str,
    sequence: int,
    character: str = "Sarah",
    action: str | None = None,
    **attributes: Any,
) -> dict[str, Any]:
    """Minimal script payload for one scene with one character."""
    scene: dict[str, Any] = {
        "scene_id": scene_id,
        "sequence": sequence,
        "characters": [{"name": character, "type": "character", **attributes}],
    }
    if action:
        scene["action"] = action
    return {"scenes": [scene]}


def footage_scene(
    scene_id: str,
    sequence: int,
    character: str = "Sarah",
    confidence: float = 0.9,
    timestamp: str = "00:10.0",
    **attributes: Any,
) -> dict[str, Any]:
    """Minimal footage payload for one scene with one detection."""
    return {
        "observations": [
            {
                "scene_id": scene_id,
                "sequence": sequence,
                "timestamp": timestamp,
                "detections": [
                    {
                        "name": character,
                        "type": "character",
                        "confidence": confidence,
                        **attributes,
                    }
                ],
            }
        ]
    }


def issue_types(report) -> set[str]:
    return {issue.type for issue in report.issues}


def find_issue(report, issue_type: str):
    return next((i for i in report.issues if i.type == issue_type), None)
