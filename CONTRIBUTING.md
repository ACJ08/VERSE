# Contributing to VERSE

**Visual & Explainable Reasoning for Semantic Evolution**
AI-powered film continuity intelligence platform.

---

## Table of Contents

1. [What Has Been Built](#what-has-been-built)
2. [Architecture Overview](#architecture-overview)
3. [Repository Layout](#repository-layout)
4. [Getting Started (Local Dev)](#getting-started-local-dev)
5. [What Needs to Be Added Next](#what-needs-to-be-added-next)
6. [Integration Contracts (Other Teams)](#integration-contracts-other-teams)
7. [Commit Convention](#commit-convention)

---

## What Has Been Built

### Frontend — React + Vite + TypeScript (`src/`)

A fully working multi-role dashboard application:

| Area | Status | Notes |
|------|--------|-------|
| Landing page | ✅ Done | Marketing + CTA |
| Auth flow | ✅ Done | Sign-up → email OTP verify → role select → onboarding → dashboard |
| Sign in | ✅ Done | Real JWT auth + one-click demo accounts (6 roles) |
| Forgot / reset password | ✅ Done | 2-step OTP flow |
| Role-based dashboard | ✅ Done | 6 roles: Producer, Director, Script Supervisor, Continuity Supervisor, Production Manager, Film Student |
| AI Analysis Modal | ✅ Done | Calls live `/continuity/analyse` endpoint; falls back to demo data if backend offline |
| Screenplay Upload UI | ✅ Done | Calls `/upload/screenplay`; shows live scene/fact counts |
| Continuity Reports | ✅ Done | Live score + issue count from engine |
| New Production / Invite Member | ✅ Done | Calls projects API |
| Backend connectivity badge | ✅ Done | "API connected" / "Demo mode" in sidebar |
| API client + React hooks | ✅ Done | `src/app/lib/api.ts` + `src/app/lib/hooks.ts` |

### Backend — FastAPI + SQLite (`continuity-engine/`)

| Area | Status | Notes |
|------|--------|-------|
| Auth (register/login/verify/reset) | ✅ Done | JWT (HS256), bcrypt, 6-digit OTP, SMTP optional |
| Projects CRUD | ✅ Done | Create/read/update/delete + team invite |
| Continuity engine | ✅ Done | 8 rule-based checks, scoring, human feedback |
| Knowledge graph | ✅ Done | NetworkX + SQLite (FactStore) |
| Screenplay upload | ✅ Done | Granite-first extractor with heuristic fallback |
| Payload deduplication | ✅ Done | SHA-256 hash guard on all ingest endpoints |
| Engine rehydration | ✅ Done | State survives process restarts |
| IBM watsonx adapter | ✅ Done | Adapter built; **credentials not wired yet** |
| LLM-backed assumption scanning | ✅ Done | Code written; **activates only when creds present** |
| LLM entity matching | ❌ Not started | Hook exists (`SemanticMatcher`) |
| LLM explanation generation | ❌ Not started | Hook exists (`ExplanationWriter`) |
| Vision model ingest | ❌ Not started | `/continuity/ingest/footage` endpoint ready |
| SMTP email | ⚠️ Optional | Works in dev without it (OTP returned in response) |
| Multi-worker deployment | ⚠️ Known gap | `_ENGINES` dict is process-local |

---

## Architecture Overview

```
Browser (React / Vite)
        │  HTTP + Bearer JWT
        ▼
FastAPI (continuity-engine/main.py — port 8000)
  ├── /auth/*          Authentication (register, login, OTP email verify/reset)
  ├── /projects/*      Project CRUD + team management
  ├── /continuity/*    Ingest → KnowledgeGraph → ConflictDetector → Report
  └── /upload/*        Screenplay file → Granite/heuristic → Ingest
        │
        ├── SQLite (verse.db)
        │     ├── users, projects, project_members
        │     ├── email_verify_tokens, password_reset_tokens
        │     └── FactStore (facts, issues, feedback) — via app/graph/storage.py
        │
        ├── ContinuityEngine (in-memory, per project_id)
        │     ├── KnowledgeGraph  — NetworkX + FactStore
        │     ├── AssumptionEngine — keyword rules + LLM hook (inactive)
        │     ├── ConflictDetector — 8 rules
        │     ├── Scorer           — category + overall
        │     ├── Reporter         — explanations + fix suggestions
        │     └── HumanFeedback   — confirm / dismiss / override
        │
        └── WatsonxAdapter (app/services/watsonx.py)
              ── Targets ibm/granite-3-8b-instruct
              ── Currently inactive (no credentials set)
              ── Degrades silently to rule-based path
```

### Data Flow

```
Screenplay (PDF/TXT)  ──►  /upload/screenplay
                                │
                                ▼  Granite (or regex fallback)
                           Structured scene JSON
                                │
                                ▼
                   /continuity/ingest/script  ──►  KnowledgeGraph
                                                         │
Footage observations  ──►  /continuity/ingest/footage ──►│
                                                         │
                                    /continuity/analyse ◄─┘
                                         │
                                         ▼
                                  ContinuityReport
                                  (score, issues, fixes)
                                         │
                              /continuity/feedback ◄── Human decision
```

---

## Repository Layout

```
VERSE/
├── src/                         React + Vite frontend
│   ├── app/
│   │   ├── pages/               LandingPage, AuthPages, OnboardingPages, DashboardPage
│   │   ├── components/ui/       shadcn/ui component library
│   │   ├── lib/
│   │   │   ├── api.ts           ← typed fetch wrapper for all backend endpoints
│   │   │   └── hooks.ts         ← React hooks (useBackendHealth, useContinuityReport, …)
│   │   └── data/mockData.ts     static mock data + UserRole / ProductionType types
│   └── styles/                  Tailwind + theme CSS
│
├── continuity-engine/           Python FastAPI backend
│   ├── main.py                  ← entry point (uvicorn main:app)
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py          ← auth endpoints
│   │   │   ├── projects.py      ← projects CRUD + engine registry
│   │   │   ├── routes.py        ← continuity engine endpoints
│   │   │   └── upload.py        ← screenplay upload + Granite/heuristic extraction
│   │   ├── core/
│   │   │   ├── database.py      ← SQLite schema + singleton connection
│   │   │   ├── security.py      ← bcrypt + JWT
│   │   │   └── dependencies.py  ← FastAPI get_current_user dependency
│   │   ├── services/
│   │   │   └── watsonx.py       ← IBM Granite adapter (inactive until creds set)
│   │   ├── engine.py            ← ContinuityEngine facade
│   │   ├── models/schemas.py    ← shared Pydantic contracts
│   │   ├── config/              ← project_config.json (weights, thresholds, aliases)
│   │   ├── graph/               ← KnowledgeGraph, FactStore, timeline
│   │   ├── ingestion/           ← dynamic JSON parser, entity matcher, normaliser
│   │   ├── reasoning/           ← 8 rules, assumptions (LLM hook), conflict detector
│   │   ├── scoring/             ← category + overall score
│   │   ├── reporting/           ← explanations, fix suggestions (LLM hook)
│   │   └── feedback/            ← human-in-the-loop confirm/dismiss/override
│   ├── docs/                    ← CONTEXT.md, INTEGRATION.md, PROGRESS.md
│   ├── examples/                ← mock script_scenes.json, footage_observations.json
│   └── tests/                   ← 47 passing tests
│
├── CONTRIBUTING.md              ← this file
├── README.md                    ← project overview
└── .env.local                   ← VITE_API_URL (not committed)
```

---

## Getting Started (Local Dev)

### 1. Backend

```bash
cd continuity-engine

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Optional: IBM watsonx SDK (only needed when credentials are available)
# pip install ibm-watsonx-ai

# Run tests (should show 47 passing)
python -m pytest

# Start the API server
uvicorn main:app --reload --port 8000
# → Open http://localhost:8000/docs for the interactive API docs
```

The server auto-seeds 6 demo accounts on first start:

| Email | Password | Role |
|-------|----------|------|
| `producer@verse.ai` | `demo2024` | Producer |
| `director@verse.ai` | `demo2024` | Director |
| `supervisor@verse.ai` | `demo2024` | Script Supervisor |
| `continuity@verse.ai` | `demo2024` | Continuity Supervisor |
| `manager@verse.ai` | `demo2024` | Production Manager |
| `student@verse.ai` | `demo2024` | Film Student |

### 2. Frontend

```bash
# From repo root
pnpm install
pnpm dev
# → Open http://localhost:5173
```

The frontend reads `VITE_API_URL` from `.env.local` (default: `http://localhost:8000`).
If the backend is not running it falls back to demo mode automatically — every auth
and data action degrades gracefully.

---

## What Needs to Be Added Next

These are the critical items required to complete the full AI-powered functionality.
Each section describes exactly what exists, what's missing, and how to wire it in.

---

### 1. IBM Granite LLM — Entity Matching + Explanations

**Status:** Adapter built and tested. Credentials not set.

**What to do:**

1. Set environment variables on the server:
   ```bash
   export WATSONX_API_KEY=<your-ibm-cloud-api-key>
   export WATSONX_PROJECT_ID=<your-watsonx-project-id>
   export WATSONX_URL=https://us-south.ml.cloud.ibm.com
   ```
2. Install the SDK:
   ```bash
   pip install ibm-watsonx-ai
   ```
3. The `WatsonxAdapter` in `app/services/watsonx.py` will automatically activate.
   It is already passed into `ContinuityEngine` as `llm=` — no other code changes needed.

**What activates automatically once credentials are set:**
- `AssumptionEngine._llm_scan_triggers()` — classifies screenplay action lines into
  disturbance categories that the keyword table would miss.
- `upload.py` `_granite_extract()` — sends raw screenplay text to Granite for
  structured scene extraction instead of the regex heuristic parser.

**What still needs to be wired (hooks exist, code not yet written):**
- `app/ingestion/entity_matcher.py` → `SemanticMatcher` class: replace fuzzy string
  matching with Granite embeddings so "Elena" and "Elena Chen" are always resolved.
- `app/reporting/explanations.py` → `ExplanationWriter`: replace templated rule-based
  text with Granite-generated natural language explanations per issue.
- `app/reporting/suggestions.py` → `SuggestionWriter`: same — Granite-generated
  fix suggestions instead of templated strings.

---

### 2. Vision Model — Footage Ingestion (Team 2)

**Status:** The ingest endpoint is ready. It needs real footage observations JSON.

**Endpoint:** `POST /continuity/ingest/footage`

**Expected JSON format** (see `continuity-engine/docs/INTEGRATION.md` for full spec):
```json
{
  "project_id": "your-project-id",
  "payload": {
    "source": "vision",
    "scenes": [
      {
        "scene_id": "SCENE_001",
        "observations": [
          {
            "entity_type": "character",
            "entity_name": "Elena Chen",
            "attribute": "wears",
            "value": "black jacket",
            "confidence": 0.91,
            "frame_ref": "shot_12_frame_240"
          }
        ]
      }
    ]
  }
}
```

**What to do:**
1. Read `continuity-engine/docs/INTEGRATION.md` — the full JSON contract is defined there.
2. Run the vision model output through the endpoint against `examples/footage_observations.json`
   to validate the format.
3. Add fixtures from real payloads to `examples/` so the team can regression-test.
4. The engine will automatically compare script facts vs footage observations and
   surface any mismatches as continuity issues.

---

### 3. Screenplay Extraction — Granite Prompt Tuning

**Status:** Granite-based extractor is written in `upload.py`. Needs real-world validation.

**What to do:**
1. Upload a real screenplay PDF once Granite credentials are set.
2. Inspect the structured JSON output at `GET /projects/{id}` (check `scenes_total`,
   `facts_count`, `entities_count`).
3. If scene/character/prop extraction is incomplete, tune the prompt in
   `upload.py → _granite_extract()`.
4. Add validated real extractions as fixtures in `examples/`.

---

### 4. Scoring Calibration

**Status:** All weights are initial estimates. Needs validation against human-scored footage.

**What to do:**
1. Have a script supervisor score a scene for continuity manually.
2. Run `POST /continuity/analyse` on the same scene.
3. Compare the engine score to the human score.
4. Tune values in `continuity-engine/app/config/project_config.json`:
   - `severity_penalties` — how many points each severity level deducts
   - `category_weights` — which categories matter most
   - `thresholds.min_observation_confidence` — reduce noise from low-quality detections

---

### 5. Multi-worker Deployment

**Status:** `_ENGINES` dict in `projects.py` is process-local — fine for dev/demo,
broken for production with multiple Uvicorn workers.

**What to do:**
- Replace `_ENGINES: dict[str, ContinuityEngine]` with a Redis-backed or
  database-backed session so all workers share the same engine state.
- The rehydration logic in `get_or_create_engine()` already handles cold starts —
  it just needs a distributed cache instead of an in-process dict.

---

### 6. SMTP Email

**Status:** Auth OTP flow fully works. In dev mode the token is returned in the
JSON response. For production:

```bash
export SMTP_HOST=smtp.yourdomain.com
export SMTP_PORT=587
export SMTP_USER=noreply@yourdomain.com
export SMTP_PASSWORD=<password>
export SMTP_FROM=noreply@yourdomain.com
```

---

## Integration Contracts (Other Teams)

| Team | Their Output | VERSE Endpoint | Docs |
|------|-------------|----------------|------|
| Team 1 (Screenplay parser) | Structured scene JSON | `POST /continuity/ingest/script` | `docs/INTEGRATION.md` |
| Team 2 (Vision / footage analysis) | Observation JSON per scene | `POST /continuity/ingest/footage` | `docs/INTEGRATION.md` |
| Team 5 (Shared backend) | Mount VERSE routers | `from app.api.routes import router` | `continuity-engine/README.md` |

Full JSON schemas and example payloads are in `continuity-engine/docs/INTEGRATION.md`.

---

## Commit Convention

```
type(scope): short description

body — what changed and why (optional, wrap at 72 chars)
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

**Examples:**
```
feat(auth): add JWT login and OTP email verification
feat(engine): wire WatsonxAdapter into AssumptionEngine
fix(routes): deduplicate ingest payloads by SHA-256 hash
docs(contributing): add LLM and vision model integration guides
```
