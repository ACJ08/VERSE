"""SQLite persistence for facts, issues and feedback.

Kept deliberately simple: the graph is rebuilt from facts on load, so SQLite
only ever stores the ground truth (facts + human decisions), never derived
state. Team 5 may swap this for Postgres by reimplementing `FactStore`.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterable

from app.models.schemas import Fact, FeedbackAction, Issue

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    fact_id     TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    entity_key  TEXT NOT NULL,
    attribute   TEXT NOT NULL,
    scene_id    TEXT,
    payload     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_facts_slot ON facts(project_id, entity_key, attribute);

CREATE TABLE IF NOT EXISTS issues (
    issue_id    TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    scene_id    TEXT,
    category    TEXT,
    status      TEXT,
    payload     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_issues_project ON issues(project_id, scene_id);

CREATE TABLE IF NOT EXISTS feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  TEXT NOT NULL,
    issue_id    TEXT NOT NULL,
    payload     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feedback_issue ON feedback(project_id, issue_id);
"""


class FactStore:
    """Persistence boundary. Use `:memory:` in tests, a file path in production."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        # A single connection keeps :memory: databases alive between calls.
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with closing(self._conn.cursor()) as cur:
            cur.executescript(_SCHEMA)
        self._conn.commit()

    # -- facts -------------------------------------------------------------- #

    def save_facts(self, project_id: str, facts: Iterable[Fact]) -> int:
        rows = [
            (
                f.fact_id,
                project_id,
                f.entity.key,
                f.attribute,
                f.scene_id,
                f.model_dump_json(),
            )
            for f in facts
        ]
        with closing(self._conn.cursor()) as cur:
            cur.executemany(
                "INSERT OR REPLACE INTO facts "
                "(fact_id, project_id, entity_key, attribute, scene_id, payload) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
        self._conn.commit()
        return len(rows)

    def load_facts(self, project_id: str, scene_id: str | None = None) -> list[Fact]:
        query = "SELECT payload FROM facts WHERE project_id = ?"
        params: list[object] = [project_id]
        if scene_id is not None:
            query += " AND scene_id = ?"
            params.append(scene_id)
        with closing(self._conn.cursor()) as cur:
            rows = cur.execute(query, params).fetchall()
        return [Fact.model_validate_json(row["payload"]) for row in rows]

    # -- issues ------------------------------------------------------------- #

    def save_issues(self, project_id: str, issues: Iterable[Issue]) -> int:
        rows = [
            (i.issue_id, project_id, i.scene_id, i.category.value, i.status.value, i.model_dump_json())
            for i in issues
        ]
        with closing(self._conn.cursor()) as cur:
            cur.executemany(
                "INSERT OR REPLACE INTO issues "
                "(issue_id, project_id, scene_id, category, status, payload) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
        self._conn.commit()
        return len(rows)

    def load_issues(self, project_id: str, scene_id: str | None = None) -> list[Issue]:
        query = "SELECT payload FROM issues WHERE project_id = ?"
        params: list[object] = [project_id]
        if scene_id is not None:
            query += " AND scene_id = ?"
            params.append(scene_id)
        with closing(self._conn.cursor()) as cur:
            rows = cur.execute(query, params).fetchall()
        return [Issue.model_validate_json(row["payload"]) for row in rows]

    # -- feedback ----------------------------------------------------------- #

    def save_feedback(self, project_id: str, action: FeedbackAction) -> None:
        with closing(self._conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO feedback (project_id, issue_id, payload) VALUES (?, ?, ?)",
                (project_id, action.issue_id, action.model_dump_json()),
            )
        self._conn.commit()

    def load_feedback(self, project_id: str) -> list[FeedbackAction]:
        with closing(self._conn.cursor()) as cur:
            rows = cur.execute(
                "SELECT payload FROM feedback WHERE project_id = ? ORDER BY id", (project_id,)
            ).fetchall()
        return [FeedbackAction.model_validate_json(row["payload"]) for row in rows]

    # -- lifecycle ---------------------------------------------------------- #

    def export(self, project_id: str) -> dict[str, list[dict]]:
        """Dump everything for a project — handy for debugging and fixtures."""
        return {
            "facts": [json.loads(f.model_dump_json()) for f in self.load_facts(project_id)],
            "issues": [json.loads(i.model_dump_json()) for i in self.load_issues(project_id)],
            "feedback": [json.loads(a.model_dump_json()) for a in self.load_feedback(project_id)],
        }

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "FactStore":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
