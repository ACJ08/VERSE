"""VERSE Backend — FastAPI Application Entry Point.

Start the server:
    cd continuity-engine
    source .venv/bin/activate
    uvicorn main:app --reload --port 8000

Then open: http://localhost:8000/docs
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.routes import router as continuity_router
from app.api.upload import router as upload_router
from app.core.database import db
from app.core.security import hash_password


# ─── Demo Account Seeder ───────────────────────────────────────────────────────

# These accounts match the one-click demo panel in src/app/pages/AuthPages.tsx.
# Each entry: (email, plaintext_password, display_name, role_id)
_DEMO_ACCOUNTS = [
    ("producer@verse.ai",    "demo2024", "Producer Demo",              "producer"),
    ("director@verse.ai",    "demo2024", "Director Demo",              "director"),
    ("supervisor@verse.ai",  "demo2024", "Script Supervisor Demo",     "script-supervisor"),
    ("continuity@verse.ai",  "demo2024", "Continuity Supervisor Demo", "continuity-supervisor"),
    ("manager@verse.ai",     "demo2024", "Production Manager Demo",    "production-manager"),
    ("student@verse.ai",     "demo2024", "Film Student Demo",          "film-student"),
]


def _seed_demo_accounts() -> None:
    """Insert demo accounts if they do not already exist. Idempotent."""
    import uuid
    from contextlib import closing

    conn = db()
    for email, password, name, role in _DEMO_ACCOUNTS:
        with closing(conn.cursor()) as cur:
            existing = cur.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            if existing is None:
                cur.execute(
                    "INSERT INTO users (id, email, name, hashed_pw, role, verified) "
                    "VALUES (?, ?, ?, ?, ?, 1)",
                    (str(uuid.uuid4()), email, name, hash_password(password), role),
                )
    conn.commit()
    print("✅  Demo accounts seeded.")


# ─── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure DB tables exist and demo accounts are present on startup
    db()
    _seed_demo_accounts()
    print("✅  VERSE backend ready  →  http://localhost:8000/docs")
    yield


# ─── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="VERSE API",
    description=(
        "Visual & Explainable Reasoning for Semantic Evolution — "
        "AI-powered film continuity intelligence platform."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ──────────────────────────────────────────────────────────────────────

_ALLOWED_ORIGINS = [
    "http://localhost:5173",   # Vite dev server
    "http://localhost:4173",   # Vite preview
    "http://127.0.0.1:5173",
]
# Allow additional origins via env var (comma-separated)
extra = os.getenv("CORS_ORIGINS", "")
if extra:
    _ALLOWED_ORIGINS.extend(o.strip() for o in extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(continuity_router)
app.include_router(upload_router)


# ─── Health + Root ─────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return {
        "name": "VERSE API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "powered_by": "IBM watsonx + IBM Granite",
    }


@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "watsonx_connected": bool(os.getenv("WATSONX_API_KEY")),
    }
