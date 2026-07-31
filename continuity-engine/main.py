"""VERSE Backend — FastAPI Application Entry Point.

This module is the single entry point for the continuity-engine server.
It is responsible for:
  - Loading environment variables from .env before any other module runs
  - Defining and registering all FastAPI routers (auth, projects, continuity, upload)
  - Seeding the SQLite database with demo accounts on first startup
  - Configuring CORS so the Vite dev server (port 5173) can reach the API
  - Exposing /health and / root endpoints consumed by the frontend status badge

Start the server:
    cd continuity-engine
    source .venv/bin/activate
    uvicorn main:app --reload --port 8000

Then open: http://localhost:8000/docs
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

# ─── Environment loading ────────────────────────────────────────────────────────
# load_dotenv() must run before any other import that calls os.getenv() at
# module level (e.g. app/core/security.py reads JWT_SECRET_KEY).
# override=False means real shell variables always win over the .env file,
# which is the correct behaviour for CI / production deployments.
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(_env_path, override=False)
except ImportError:
    # python-dotenv is listed in requirements.txt; if it is somehow missing,
    # fall back gracefully — the server still works via shell environment vars.
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers — each module owns its own APIRouter; we register them here so the
# URL prefix structure is visible in one place.
from app.api.auth import router as auth_router          # /auth/*
from app.api.projects import router as projects_router  # /projects/*
from app.api.routes import router as continuity_router  # /continuity/*
from app.api.upload import router as upload_router      # /upload/*
from app.core.database import db
from app.core.security import hash_password


# ─── Demo Account Seeder ───────────────────────────────────────────────────────
# These six accounts match the one-click demo panel in AuthPages.tsx.
# They are inserted once on startup and never updated; changing the password
# here only takes effect on a fresh database (delete verse.db to reset).
# Format: (email, plaintext_password, display_name, role_id)
_DEMO_ACCOUNTS = [
    ("producer@verse.ai",    "demo2024", "Producer Demo",              "producer"),
    ("director@verse.ai",    "demo2024", "Director Demo",              "director"),
    ("supervisor@verse.ai",  "demo2024", "Script Supervisor Demo",     "script-supervisor"),
    ("continuity@verse.ai",  "demo2024", "Continuity Supervisor Demo", "continuity-supervisor"),
    ("manager@verse.ai",     "demo2024", "Production Manager Demo",    "production-manager"),
    ("student@verse.ai",     "demo2024", "Film Student Demo",          "film-student"),
]


def _seed_demo_accounts() -> None:
    """Insert demo accounts if they do not already exist. Safe to call repeatedly (idempotent)."""
    import uuid
    from contextlib import closing

    conn = db()
    for email, password, name, role in _DEMO_ACCOUNTS:
        with closing(conn.cursor()) as cur:
            # Skip if the account already exists — avoids duplicate key errors
            # and preserves any password changes made through the reset flow.
            existing = cur.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            if existing is None:
                cur.execute(
                    "INSERT INTO users (id, email, name, hashed_pw, role, verified) "
                    "VALUES (?, ?, ?, ?, ?, 1)",
                    # verified=1 so demo accounts skip the email verification step
                    (str(uuid.uuid4()), email, name, hash_password(password), role),
                )
    conn.commit()
    print("✅  Demo accounts seeded.")


# ─── Lifespan ──────────────────────────────────────────────────────────────────
# FastAPI lifespan runs once on startup (before any request is served) and once
# on shutdown. We use it to initialise the database schema and seed demo data.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # db() creates all tables defined in _SCHEMA if they do not yet exist.
    db()
    _seed_demo_accounts()
    print("✅  VERSE backend ready  →  http://localhost:8000/docs")
    yield
    # Nothing to clean up on shutdown; SQLite WAL is flushed automatically.


# ─── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="VERSE API",
    description=(
        "Visual & Explainable Reasoning for Semantic Evolution — "
        "AI-powered film continuity intelligence platform."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",    # Swagger UI  — useful for manual testing during development
    redoc_url="/redoc",  # ReDoc UI    — cleaner reading experience for the team
)

# ─── CORS ──────────────────────────────────────────────────────────────────────
# Allow the Vite dev server and preview server by default.
# Additional origins (e.g. a staging URL) can be added via the CORS_ORIGINS
# environment variable as a comma-separated list — see .env.example.
_ALLOWED_ORIGINS = [
    "http://localhost:5173",   # Vite dev server (pnpm dev)
    "http://localhost:4173",   # Vite preview server (pnpm preview)
    "http://127.0.0.1:5173",   # Same as above, loopback variant
]
extra = os.getenv("CORS_ORIGINS", "")
if extra:
    # Extend the list at runtime without touching this file
    _ALLOWED_ORIGINS.extend(o.strip() for o in extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,   # Required so the browser sends the JWT cookie / header
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ───────────────────────────────────────────────────────────────────
# Register every router. Prefix and tags are defined inside each router module
# so this section stays a flat, readable list.
app.include_router(auth_router)        # POST /auth/register, /auth/login, /auth/me, …
app.include_router(projects_router)    # GET/POST/PATCH/DELETE /projects, /projects/{id}/team
app.include_router(continuity_router)  # POST /continuity/analyse, /continuity/ingest/*, …
app.include_router(upload_router)      # POST /upload/screenplay, /upload/footage, /upload/call-sheet


# ─── Health + Root ─────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    """Minimal root response — useful for a quick "is the server alive?" check."""
    return {
        "name": "VERSE API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "powered_by": "IBM watsonx + IBM Granite",
    }


@app.get("/health", tags=["system"])
def health():
    """
    Health check consumed by the frontend BackendStatusBadge component.
    Returns the server status and whether IBM watsonx credentials are present.
    watsonx_connected=false does NOT mean the server is broken — it just means
    AI-enhanced explanations and screenplay extraction will use rule-based fallbacks.
    """
    return {
        "status": "ok",
        "version": "0.1.0",
        # Non-empty WATSONX_API_KEY means the Granite LLM features are active
        "watsonx_connected": bool(os.getenv("WATSONX_API_KEY")),
    }
