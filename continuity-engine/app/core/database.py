"""Unified SQLite database for auth + project metadata.

The continuity engine's FactStore handles fact/issue persistence.
This module handles: users, sessions, and project metadata.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parents[2] / "verse.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    hashed_pw   TEXT NOT NULL,
    role        TEXT DEFAULT 'producer',
    verified    INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS projects (
    id              TEXT PRIMARY KEY,
    owner_id        TEXT NOT NULL,
    name            TEXT NOT NULL,
    workspace_name  TEXT NOT NULL,
    production_type TEXT DEFAULT 'feature-film',
    status          TEXT DEFAULT 'In Production',
    description     TEXT DEFAULT '',
    start_date      TEXT DEFAULT '',
    end_date        TEXT DEFAULT '',
    team_size       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS project_members (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  TEXT NOT NULL,
    user_id     TEXT,
    email       TEXT NOT NULL,
    role        TEXT DEFAULT 'department-member',
    status      TEXT DEFAULT 'invited',
    joined_at   TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_members_project ON project_members(project_id);
"""


def get_conn(path: str | Path | None = None) -> sqlite3.Connection:
    """Return a shared connection for the given db path (default: verse.db)."""
    p = str(path or _DB_PATH)
    if p != ":memory:":
        Path(p).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    with closing(conn.cursor()) as cur:
        cur.executescript(_SCHEMA)
    conn.commit()
    return conn


# Module-level singleton connection (safe for single-worker dev server)
_conn: sqlite3.Connection | None = None


def db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = get_conn()
    return _conn
