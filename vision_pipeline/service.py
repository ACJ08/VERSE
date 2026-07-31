"""HTTP wrapper around the vision pipeline.

The CLI in `main.py` writes `scene_<id>.json` to disk. That works for one clip
at a time on the machine that has the models; it does not let the VERSE backend
process footage a user uploaded through the dashboard. This service exposes the
same pipeline over HTTP so the continuity engine can call it:

    uvicorn service:app --port 8200

Then point the continuity engine at it:

    VISION_SERVICE_URL=http://localhost:8200

The detection code is imported from `main.py` rather than duplicated — the CLI
and the service always produce byte-identical documents.

Endpoints
    GET  /health              model status, no video required
    POST /process             video -> scene document (the JSON the CLI writes)
    POST /process/ingest      video -> scene document -> POST to the engine

Models are loaded once and reused. Loading YOLO and MediaPipe takes seconds, so
a per-request load would dominate the response time.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
except ImportError:
    pass  # python-dotenv not installed — rely on shell environment variables

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from main import build_observations
from src.frame_extractor import extract_frames
from src.object_detector import ObjectDetector
from src.pose_estimator import PoseEstimator
from src.tracker import CentroidTracker

DEFAULT_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
DEFAULT_POSE_MODEL = os.getenv("POSE_MODEL", "pose_landmarker_lite.task")
DEFAULT_FPS = float(os.getenv("SAMPLE_FPS", "2.0"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "200"))

# Continuity engine to forward to. Used by /process/ingest.
ENGINE_URL = os.getenv("CONTINUITY_ENGINE_URL", "http://localhost:8000").rstrip("/")

app = FastAPI(
    title="VERSE Vision Service",
    description=(
        "Footage processing for VERSE: video in, structured per-frame "
        "observations out. Wraps the vision_pipeline CLI."
    ),
    version="0.1.0",
)

# ─── Model cache ──────────────────────────────────────────────────────────────

_detectors: dict[tuple[str, float, float], ObjectDetector] = {}
_pose_estimators: dict[str, PoseEstimator] = {}


def _detector(model: str, conf: float, iou: float) -> ObjectDetector:
    key = (model, conf, iou)
    if key not in _detectors:
        _detectors[key] = ObjectDetector(model, conf_threshold=conf, iou_threshold=iou)
    return _detectors[key]


def _pose_estimator(model: str) -> PoseEstimator:
    if model not in _pose_estimators:
        _pose_estimators[model] = PoseEstimator(model)
    return _pose_estimators[model]


# ─── Core ─────────────────────────────────────────────────────────────────────


def process_clip(
    video_path: str,
    scene_id: str,
    *,
    fps: float = DEFAULT_FPS,
    model: str = DEFAULT_MODEL,
    pose_model: str = DEFAULT_POSE_MODEL,
    conf: float = 0.5,
    iou: float = 0.45,
) -> dict[str, Any]:
    """Run the pipeline over one clip and return the scene document."""
    try:
        frames, source_fps = extract_frames(video_path, target_fps=fps)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    if not frames:
        raise HTTPException(422, "No frames could be read from the uploaded video.")

    frame_width = frames[0].image.shape[1]
    observations, _raw, _hands = build_observations(
        frames,
        _detector(model, conf, iou),
        CentroidTracker(max_distance=0.3 * frame_width),
        _pose_estimator(pose_model),
    )

    return {
        "scene_id": scene_id,
        "observations": observations,
        # Envelope metadata: the engine's parser skips these keys rather than
        # turning them into facts.
        "frames_analysed": len(frames),
        "source_fps": round(source_fps, 2),
    }


async def _save_upload(video: UploadFile) -> Path:
    if video.size and video.size > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {MAX_UPLOAD_MB} MB limit.")
    data = await video.read()
    if not data:
        raise HTTPException(400, "Uploaded file is empty.")

    suffix = Path(video.filename or "clip.mp4").suffix or ".mp4"
    handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        handle.write(data)
    finally:
        handle.close()
    return Path(handle.name)


# ─── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "yolo_model": DEFAULT_MODEL,
        "pose_model": DEFAULT_POSE_MODEL,
        "pose_model_present": Path(DEFAULT_POSE_MODEL).exists(),
        "models_loaded": len(_detectors) > 0,
        "engine_url": ENGINE_URL,
    }


@app.post("/process")
async def process(
    video: UploadFile = File(..., description="Video clip to analyse"),
    scene_id: str = Form(..., description="Scene identifier, e.g. SCENE_001"),
    fps: float = Form(DEFAULT_FPS),
    conf: float = Form(0.5),
    iou: float = Form(0.45),
) -> dict[str, Any]:
    """Analyse a clip and return the same document the CLI writes to disk."""
    path = await _save_upload(video)
    try:
        return process_clip(str(path), scene_id, fps=fps, conf=conf, iou=iou)
    finally:
        path.unlink(missing_ok=True)


@app.post("/process/ingest")
async def process_and_ingest(
    video: UploadFile = File(...),
    scene_id: str = Form(...),
    project_id: str = Form("VERSE_DEMO"),
    engine_url: str = Form(ENGINE_URL),
    entity_aliases: str | None = Form(
        None, description='JSON object joining track ids to script names, e.g. {"PERSON_1": "Sarah"}'
    ),
    analyse: bool = Form(True),
    fps: float = Form(DEFAULT_FPS),
) -> dict[str, Any]:
    """Analyse a clip and push the result straight into the continuity engine.

    Posts to `/continuity/ingest-adapted/footage`, which aggregates the frames
    and compares them against whatever the script said about the same scene.
    """
    import json

    import httpx

    path = await _save_upload(video)
    try:
        document = process_clip(str(path), scene_id, fps=fps)
    finally:
        path.unlink(missing_ok=True)

    aliases: dict[str, Any] | None = None
    if entity_aliases and entity_aliases.strip():
        try:
            parsed = json.loads(entity_aliases)
        except ValueError as exc:
            raise HTTPException(422, f"entity_aliases must be valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise HTTPException(422, "entity_aliases must be a JSON object.")
        aliases = parsed

    url = f"{engine_url.rstrip('/')}/continuity/ingest-adapted/footage"
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                url,
                json={
                    "project_id": project_id,
                    "payload": document,
                    "scene_id": scene_id,
                    "entity_aliases": aliases,
                    "analyse": analyse,
                },
            )
            response.raise_for_status()
            ingested = response.json()
    except Exception as exc:  # noqa: BLE001 - report, do not lose the analysis
        raise HTTPException(
            502,
            f"Analysed {document['frames_analysed']} frames but could not reach the "
            f"continuity engine at {url}: {exc}",
        ) from exc

    return {"scene_document": document, "ingestion": ingested}
