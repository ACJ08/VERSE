"""Projects router — workspace CRUD + team management.

Responsibilities
----------------
* Full CRUD for project records stored in the SQLite `projects` table.
* Team management: list members, invite by email.
* Engine Registry: each project_id maps to exactly one ContinuityEngine
  instance that is kept alive in the worker process (_ENGINES dict).
  On a cold cache miss (first access or after a process restart) the engine is
  rehydrated from FactStore so no ingested data is ever lost.
* Ingestion deduplication: SHA-256 hashes of previously ingested payloads are
  stored in _INGESTED_HASHES so the same JSON payload cannot be ingested twice
  (prevents doubled facts from retried requests).

All endpoints require a valid JWT via Depends(get_current_user).
"""

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
# One ContinuityEngine per project, kept alive for the lifetime of the process.
# Hot path: O(1) dict lookup on every request.
# Cold path (first access / restart): rehydrate from FactStore then cache.
#
# Multi-worker note: this dict is process-local, so uvicorn --workers N will
# create N independent caches. For production replace with Redis + shared DB.

_ENGINES: dict[str, ContinuityEngine] = {}

# Shared SQLite-backed FactStore. All engines in this process write to the
# same database file so state persists across restarts and between workers
# (as long as only one worker writes at a time — use --workers 1 for now).
_STORE = FactStore(str(__import__("pathlib").Path(__file__).resolve().parents[2] / "verse.db"))


def get_or_create_engine(project_id: str) -> ContinuityEngine:
    """Return the cached ContinuityEngine for *project_id*.

    On a cache miss the engine is constructed, then rehydrated from FactStore
    so the in-memory knowledge graph matches the persisted state.

    LLM selection order (most capable → least capable):
    1. LangChain model via VERSE_LLM_MODEL env var (any provider — Anthropic,
       OpenAI, IBM, etc.). Configured in services/langchain_adapter.py.
    2. IBM WatsonxAdapter if WATSONX_API_KEY + WATSONX_PROJECT_ID are set.
    3. None → rule-based fallbacks; reports are still complete and accurate.

    Semantic matcher order:
    1. Granite embedding matcher (requires WatsonxAdapter with credentials).
    2. keyword_semantic_matcher built from the project's value_synonyms config.
    """
    if project_id not in _ENGINES:
        config = ProjectConfig.from_dict({"project_id": project_id})

        # Import lazily so the module can be imported even without langchain installed
        from app.services.langchain_adapter import create_llm_from_env
        from app.services.watsonx import create_llm, create_semantic_matcher

        watsonx = create_llm()                          # returns None if no credentials
        llm = create_llm_from_env() or watsonx          # prefer LangChain; fall back to watsonx
        semantic_matcher = create_semantic_matcher(watsonx)  # None when watsonx is unavailable

        engine = ContinuityEngine(
            config=config,
            store=_STORE,
            llm=llm,
            semantic_matcher=semantic_matcher,
        )

        # ── Rehydration ─────────────────────────────────────────────────────
        # Replay persisted facts into the in-memory graph so that a restart
        # does not lose previously ingested screenplay or footage data.
        facts = _STORE.load_facts(project_id)
        if facts:
            # add_facts() returns the deduplicated subset that was actually added
            stored = engine.graph.add_facts(facts)
            # Re-prime the assumption engine so TTL countdown resumes correctly
            engine.assumptions.ingest(stored, engine.graph.timeline.sequence_of)

        # Restore human feedback so dismissed patterns are honoured immediately
        # without requiring the user to re-dismiss them after every restart.
        feedback_actions = _STORE.load_feedback(project_id)
        for action in feedback_actions:
            engine.feedback.apply(action, [])

        _ENGINES[project_id] = engine

    return _ENGINES[project_id]


# ─── Ingestion deduplication ──────────────────────────────────────────────────
# Keeps a per-project set of payload SHA-256 hashes so a client that sends the
# same JSON twice (e.g. on retry after a network blip) is silently idempotent.
# The set lives in memory so it resets on restart — acceptable because the
# FactStore's own deduplication logic prevents double-saves to the graph.

_INGESTED_HASHES: dict[str, set[str]] = {}


def payload_hash(payload: object) -> str:
    """Return the SHA-256 hex digest of *payload* serialised to canonical JSON."""
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


def is_duplicate_payload(project_id: str, h: str) -> bool:
    """Return True if *h* has already been ingested for *project_id*."""
    return h in _INGESTED_HASHES.get(project_id, set())


def record_payload_hash(project_id: str, h: str) -> None:
    """Mark payload hash *h* as ingested for *project_id*."""
    _INGESTED_HASHES.setdefault(project_id, set()).add(h)


# ─── Request / Response models ─────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    """Fields accepted when creating a new project workspace."""
    name: str                              # Human-readable production title, e.g. "The Last Scene"
    workspace_name: str = ""               # Auto-generated from name if blank: "VERSE — {name}"
    production_type: str = "feature-film"  # feature-film | tv-series | documentary | …
    description: str = ""
    start_date: str = ""                   # ISO-8601 date string, e.g. "2024-06-01"
    end_date: str = ""
    team_size: int = 1                     # Estimated headcount — informational only


class UpdateProjectRequest(BaseModel):
    """Partial update — only non-None fields are written to the database."""
    name: str | None = None
    workspace_name: str | None = None
    production_type: str | None = None
    status: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    team_size: int | None = None


class InviteMemberRequest(BaseModel):
    """Invite a team member by email address."""
    email: str
    role: str = "department-member"  # producer | director | script-supervisor | …


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _project_or_404(project_id: str, user_id: str) -> dict:
    """Fetch project row or raise 404; raise 403 if caller is neither owner nor member."""
    conn = db()
    with closing(conn.cursor()) as cur:
        row = cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"Project '{project_id}' not found.")
    p = dict(row)
    if p["owner_id"] == user_id:
        return p
    # Allow invited team members to read the project too.
    with closing(conn.cursor()) as cur:
        member = cur.execute(
            "SELECT id FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, user_id),
        ).fetchone()
    if member is None:
        raise HTTPException(403, "You do not have access to this project.")
    return p


def _row_to_project(row: dict) -> dict:
    """Enrich a raw project DB row with live stats from the engine graph.

    scenes_total, facts_count, and entities_count are stored in the knowledge
    graph (not the DB), so they must be read from the engine at query time.
    Falls back to zeros if the engine is not initialised or throws.
    """
    proj = dict(row)
    try:
        engine = get_or_create_engine(proj["id"])
        stats = engine.stats()
        proj["scenes_total"] = stats.get("scenes", 0)
        proj["facts_count"] = stats.get("facts", 0)
        proj["entities_count"] = stats.get("entities", 0)
    except Exception:
        # Engine startup failure (e.g. bad config) — return zeros rather than 500
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
    """Create a new project workspace and initialise its ContinuityEngine.

    Returns the full project dict enriched with engine stats (all zeros on
    creation since no data has been ingested yet).
    """
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

    # Warm up the engine cache so the first ingest/analyse is not slow
    get_or_create_engine(project_id)
    return _row_to_project(row)


@router.get("")
def list_projects(current_user: Annotated[dict, Depends(get_current_user)]):
    """Return all projects owned by the caller, newest first, with live stats."""
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
    """Fetch a single project with live engine stats."""
    return _row_to_project(_project_or_404(project_id, current_user["id"]))


@router.patch("/{project_id}")
def update_project(
    project_id: str,
    req: UpdateProjectRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Partial update — only sends the fields you want to change."""
    _project_or_404(project_id, current_user["id"])
    # Build the SET clause dynamically from non-None fields
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
    """Delete a project, its team memberships, and evict it from the engine cache."""
    _project_or_404(project_id, current_user["id"])
    conn = db()
    with closing(conn.cursor()) as cur:
        cur.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        cur.execute("DELETE FROM project_members WHERE project_id = ?", (project_id,))
    conn.commit()
    # Free the in-memory engine so stale data cannot be re-used
    _ENGINES.pop(project_id, None)
    _INGESTED_HASHES.pop(project_id, None)


@router.get("/{project_id}/team")
def get_team(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List all team members for a project, ordered by invitation date."""
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
    """Invite a team member by email address.

    If the email matches an existing VERSE account the invitation is linked to
    that user's id immediately. Otherwise it stays pending until the person
    registers.
    """
    _project_or_404(project_id, current_user["id"])
    conn = db()
    with closing(conn.cursor()) as cur:
        # Prevent duplicate invitations for the same email
        existing = cur.execute(
            "SELECT id FROM project_members WHERE project_id = ? AND email = ?",
            (project_id, req.email.lower()),
        ).fetchone()
        if existing:
            raise HTTPException(409, "This email has already been invited.")

        # Link to an existing account if one exists; leave user_id NULL otherwise
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
