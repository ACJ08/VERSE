"""MOCK stand-in for team 5 (Backend Integration & Deployment).

    python demo/server.py     ->  http://127.0.0.1:8000

Mounts the real continuity router and adds demo-only endpoints that run the
mock upstream teams, so the dashboard has a live API to talk to. Team 5 will
replace this file; the router it mounts is the part that stays.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "continuity-engine"))
sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import HTMLResponse, JSONResponse  # noqa: E402

from app.api.routes import router  # noqa: E402  <- the real thing
from demo.pipeline import SCREENPLAY, build_engine  # noqa: E402
from demo.mocks import script_extractor, vision_detector  # noqa: E402

app = FastAPI(title="VERSE demo", version="0.1.0")
app.include_router(router)


@app.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    """Serve the baked dashboard, building it on first request if needed."""
    page = HERE / "dashboard.html"
    if not page.exists():
        from demo.build_dashboard import build

        build()
    return HTMLResponse(page.read_text(encoding="utf-8"))


@app.get("/demo/report")
def demo_report() -> JSONResponse:
    """Run the whole pipeline fresh and return the report."""
    engine, script_json, footage_json = build_engine()
    report = engine.analyse()
    return JSONResponse(
        {
            "report": json.loads(report.model_dump_json()),
            "script": script_json,
            "footage": footage_json,
            "stats": engine.stats(),
            "planted_errors": vision_detector.expected_findings(),
        }
    )


@app.get("/demo/script")
def demo_script() -> JSONResponse:
    """What the mock Granite extractor produced (team 1's contract)."""
    return JSONResponse(script_extractor.extract_file(SCREENPLAY))


@app.get("/demo/footage")
def demo_footage() -> JSONResponse:
    """What the mock vision detector produced (team 2's contract)."""
    return JSONResponse(vision_detector.detect(script_extractor.extract_file(SCREENPLAY)))


if __name__ == "__main__":
    print("VERSE demo -> http://127.0.0.1:8000")
    print("  /               dashboard")
    print("  /docs           OpenAPI for the real continuity router")
    print("  /demo/report    full pipeline output")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
