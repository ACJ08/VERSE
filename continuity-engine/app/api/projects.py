"""Projects router — workspace CRUD + team management."""

from __future__ import annotations

import hashlib
import json
import uuid
from contextlib import closing
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import db
from app.core.dependencies import get_current_user
from app.engine import ContinuityEngine
from app.config import ProjectConfig
from app.graph.storage import FactStore

router = APIRouter(prefix="/projects", tags=["projects"])

# ─── Engine Registry ──────────────────────────────────────────────────────────
#
# Engines are cached in-process for performance. On a cold hit (process
# restart or a project_id that was never seen in this worker) we rehydrate
# the engine from FactStore so no state is lost across restarts.
#
# For multi-worker production deployments replace the in-process dict with
# Redis or a DB-backed session; the rehydration logic below stays the same.

_ENGINES: dict[str, ContinuityEngine] = {}
_STORE = FactStore(str(__import__("pathlib").Path(__file__).resolve().parents[2] / "verse.db"))


def get_or_create_engine(project_id: str) -> ContinuityEngine:
    """Return the cached engine for *project_id*, rehydrating from FactStore if needed."""
    if project_id not in _ENGINES:
        config = ProjectConfig.from_dict({"project_id": project_id})
        from app.services.watsonx import create_llm
        engine = ContinuityEngine(config=config, store=_STORE, llm=create_llm())
        # Rehydrate: replay stored facts so the in-memory graph is consistent
        # with what was persisted before a restart.
        facts = _STORE.load_facts(project_id)
        if facts:
            # Re-add facts directly to the graph (skip re-saving to store)
            stored = engine.graph.add_facts(facts)
            engine.assumptions.ingest(stored, engine.graph.timeline.sequence_of)
        # Restore human feedback decisions so dismissed patterns carry over.
        feedback_actions = _STORE.load_feedback(project_id)
        for action in feedback_actions:
            engine.feedback.apply(action, [])
        _ENGINES[project_id] = engine
    return _ENGINES[project_id]


# ─── Ingestion deduplication ──────────────────────────────────────────────────
#
# Keeps a set of SHA-256 hashes of payloads already ingested per project.
# This prevents a repeated POST of the same JSON from doubling every fact.

_INGESTED_HASHES: dict[str, set[str]] = {}


def payload_hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


def is_duplicate_payload(project_id: str, h: str) -> bool:
    return h in _INGESTED_HASHES.get(project_id, set())


def record_payload_hash(project_id: str, h: str) -> None:
    _INGESTED_HASHES.setdefault(project_id, set()).add(h)


# ─── Request / Response models ─────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str
    workspace_name: str = ""
    production_type: str = "feature-film"
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    team_size: int = 1


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    workspace_name: str | None = None
    production_type: str | None = None
    status: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    team_size: int | None = None


class InviteMemberRequest(BaseModel):
    email: str
    role: str = "department-member"


def _project_or_404(project_id: str, user_id: str) -> dict:
    conn = db()
    with closing(conn.cursor()) as cur:
        row = cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"Project '{project_id}' not found.")
    p = dict(row)
    if p["owner_id"] != user_id:
        raise HTTPException(403, "You do not have access to this project.")
    return p


def _row_to_project(row: dict) -> dict:
    """Enrich a project row with live engine stats."""
    proj = dict(row)
    try:
        engine = get_or_create_engine(proj["id"])
        stats = engine.stats()
        proj["scenes_total"] = stats.get("scenes", 0)
        proj["facts_count"] = stats.get("facts", 0)
        proj["entities_count"] = stats.get("entities", 0)
    except Exception:
        proj["scenes_total"] = 0
        proj["facts_count"] = 0
        proj["entities_count"] = 0
    return proj


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_project(
    req: CreateProjectRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    project_id = str(uuid.uuid4())
    ws_name = req.workspace_name or f"VERSE — {req.name}"
    conn = db()
    with closing(conn.cursor()) as cur:
        cur.execute(
            """INSERT INTO projects
               (id, owner_id, name, workspace_name, production_type,
                description, start_date, end_date, team_size)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, current_user["id"], req.name, ws_name,
             req.production_type, req.description, req.start_date,
             req.end_date, req.team_size),
        )
        conn.commit()
        row = dict(cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())

    # Initialise a ContinuityEngine for this project
    get_or_create_engine(project_id)
    return _row_to_project(row)


@router.get("")
def list_projects(current_user: Annotated[dict, Depends(get_current_user)]):
    conn = db()
    with closing(conn.cursor()) as cur:
        rows = cur.execute(
            "SELECT * FROM projects WHERE owner_id = ? ORDER BY created_at DESC",
            (current_user["id"],),
        ).fetchall()
    return [_row_to_project(dict(r)) for r in rows]


@router.get("/{project_id}")
def get_project(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    return _row_to_project(_project_or_404(project_id, current_user["id"]))


@router.patch("/{project_id}")
def update_project(
    project_id: str,
    req: UpdateProjectRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    _project_or_404(project_id, current_user["id"])
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update.")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn = db()
    with closing(conn.cursor()) as cur:
        cur.execute(
            f"UPDATE projects SET {set_clause} WHERE id = ?",
            [*updates.values(), project_id],
        )
        conn.commit()
        row = dict(cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
    return _row_to_project(row)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    _project_or_404(project_id, current_user["id"])
    conn = db()
    with closing(conn.cursor()) as cur:
        cur.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        cur.execute("DELETE FROM project_members WHERE project_id = ?", (project_id,))
    conn.commit()
    _ENGINES.pop(project_id, None)
    _INGESTED_HASHES.pop(project_id, None)


@router.get("/{project_id}/team")
def get_team(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    _project_or_404(project_id, current_user["id"])
    conn = db()
    with closing(conn.cursor()) as cur:
        members = cur.execute(
            "SELECT * FROM project_members WHERE project_id = ? ORDER BY joined_at",
            (project_id,),
        ).fetchall()
    return [dict(m) for m in members]


@router.post("/{project_id}/team/invite", status_code=201)
def invite_member(
    project_id: str,
    req: InviteMemberRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    _project_or_404(project_id, current_user["id"])
    conn = db()
    with closing(conn.cursor()) as cur:
        # Check if already invited
        existing = cur.execute(
            "SELECT id FROM project_members WHERE project_id = ? AND email = ?",
            (project_id, req.email.lower()),
        ).fetchone()
        if existing:
            raise HTTPException(409, "This email has already been invited.")

        # Try to find user by email
        user_row = cur.execute("SELECT id FROM users WHERE email = ?", (req.email.lower(),)).fetchone()
        cur.execute(
            """INSERT INTO project_members (project_id, user_id, email, role)
               VALUES (?, ?, ?, ?)""",
            (project_id, user_row["id"] if user_row else None,
             req.email.lower(), req.role),
        )
        conn.commit()

    return {
        "invited": True,
        "email": req.email.lower(),
        "role": req.role,
        "message": f"Invite sent to {req.email}.",
    }
