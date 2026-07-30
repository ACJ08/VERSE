# VERSE Vision Pipeline

Footage-processing half of VERSE, a film-continuity system. Turns a video clip into
structured JSON describing what's on screen (characters, props, hand usage, screen
position, movement, costume color) so a separate comparison step can diff it against
the script-analysis side (script text -> the same structured shape via IBM Granite)
and flag continuity errors. This pipeline only *describes* what it sees — it does not
judge continuity errors.

Local-only: OpenCV + Ultralytics YOLO (COCO-pretrained) + MediaPipe Pose. No cloud
API, no model training.

## Status

All 5 build steps are implemented and running end-to-end on a real clip
(person holding/drinking from a wine glass).

| Step | What it does |
|---|---|
| 1 | Frame extraction via OpenCV, sampled at ~2fps |
| 2 | YOLO person detection, screen position (left/center/right) from bbox center |
| 3 | Glass/cup prop detection (COCO `wine glass`/`cup`), confidence threshold + IoU dedup, simple centroid tracking for stable person IDs |
| 4 | MediaPipe Pose wrist keypoints, nearest-wrist prop association -> `hand_usage`, with a plausibility gate (rejects off-frame or implausibly-far wrist estimates) |
| 5 | Final schema: `scene_<id>.json`, `HH:MM:SS.mmm` timestamps, movement (bbox-center delta between sampled frames), best-effort costume color |

## Setup

```powershell
cd vision_pipeline
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

First run auto-downloads `yolov8n.pt` (Ultralytics) and needs
`pose_landmarker_lite.task` (MediaPipe) in the project root:

```powershell
python -c "import urllib.request; urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task', 'pose_landmarker_lite.task')"
```

## Usage

```powershell
python main.py --video path\to\clip.mp4 --scene-id SCENE_001
```

Writes `scene_001.json` (filename = scene-id lowercased) and `debug_frame.jpg`
(an annotated frame for visually sanity-checking detections/wrists/associations).

### CLI options

| Flag | Default | Purpose |
|---|---|---|
| `--video` | required | Input clip path |
| `--scene-id` | required | Applied to every observation; also derives the output filename |
| `--fps` | 2.0 | Frame sampling rate |
| `--out` | `<scene-id>.json` | Override output path |
| `--model` | `yolov8n.pt` | YOLO weights |
| `--pose-model` | `pose_landmarker_lite.task` | MediaPipe pose model bundle |
| `--conf` | 0.5 | Minimum YOLO detection confidence |
| `--iou` | 0.45 | IoU threshold for deduplicating overlapping same-class boxes |
| `--debug-out` | `debug_frame.jpg` | Annotated debug frame path |
| `--debug-frame-id` | most-detections frame | Force a specific frame for the debug image |

## Output schema

```json
{
  "scene_id": "SCENE_001",
  "observations": [
    {
      "frame_id": 2,
      "timestamp": "00:00:00.960",
      "characters": [
        { "name": "PERSON_1", "costume": "black", "position": "left", "movement": "stationary", "emotional_state": null }
      ],
      "props": [
        { "name": "wine glass", "hand_usage": "left", "state": null, "owner": null }
      ],
      "detections": [
        { "type": "character", "name": "PERSON_1", "confidence": 0.556 },
        { "type": "prop", "name": "wine glass", "confidence": 0.737 }
      ]
    }
  ]
}
```

`characters[]` and `props[]` match the teammate's Pydantic `Character`/`Prop` models
field-for-field, with no extra keys. Detection confidence is **not** on those objects
(the models don't define it) — it lives in the sibling `detections[]` array per
observation, referencing items by `name`.

- `Character.name` — uppercase placeholder (`PERSON_1`, `PERSON_2`, ...) from the
  centroid tracker, not an identified script character name. Identity resolution
  against script character names is out of scope for this pipeline.
- `Prop.hand_usage` — one of `left`/`right`/`both`/`none`. Uses MediaPipe's
  **anatomical** left/right (the subject's own hands), not mirrored screen space —
  matches how a script would describe it ("her left hand").
- `movement` — `null` on a track's first sighting (nothing to compare yet), else
  `stationary`/`moving` from bbox-center delta between consecutive sampled frames.
- `costume` — best-effort dominant torso color name (median RGB -> nearest named
  color). Not garment-aware; weak on dark/desaturated clothing (see Known
  limitations).
- `emotional_state`, `owner`, `state` — always `null`; not vision-detectable.

## HTTP service

`service.py` exposes the same pipeline over HTTP so the VERSE backend can process
footage a user uploaded through the dashboard, instead of someone running the CLI
by hand. Detection code is imported from `main.py`, so the CLI and the service
emit byte-identical documents.

```powershell
uvicorn service:app --port 8200
```

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Model status; confirms `pose_landmarker_lite.task` is present |
| POST | `/process` | `video` + `scene_id` → the scene document shown above |
| POST | `/process/ingest` | Same, then POSTs it to the continuity engine and returns its report |

Models load once per process and are reused — loading YOLO and MediaPipe takes
seconds and would otherwise dominate every request.

Point the continuity engine at this service so its `/upload/footage` endpoint can
accept raw video rather than only pre-computed JSON:

```
VISION_SERVICE_URL=http://localhost:8200
```

## Known limitations

- **`PERSON_n` placeholder names are not script character names.** The tracker
  cannot know who it is looking at, so identity resolution happens at ingestion:
  the engine's vision adapter takes an `entity_aliases` map
  (`{"PERSON_1": "Sarah"}`) that joins track ids to script names, and warns when
  a payload arrives with unmapped `PERSON_n` ids. Without a mapping, footage
  facts register as their own entities and no comparison happens for that person
  — supply the map from the dashboard's footage upload dialog, per-request on
  `/continuity/ingest-adapted/footage`, or in the project's `entity_aliases`
  config table. Track-id churn (below) means the mapping is per clip, not global.
- **`hand_usage` is modelled on the Prop entity, not on the Character holding
  it.** `owner` is always null here because the pipeline cannot attribute a prop
  to a person. The engine's vision adapter closes the gap where it is safe to:
  in a frame with exactly one detected person and a prop associated to a wrist,
  it emits `holds` / `held_in_hand` on that character with
  `source: "ai_inference"`, so the claim is compared but trusted below direct
  detection. With two or more people in frame nothing is inferred.
- **`hand_usage` requires a detected character.** MediaPipe Pose runs independently
  of YOLO's person detection, so it could find wrists in a frame where YOLO found
  no person (e.g. below the confidence threshold). If a frame has no detected
  character, every prop's `hand_usage` is forced to `"none"` — there's no body for
  the wrist association to come from, regardless of what Pose reports.
- **Costume color is unreliable on dark clothing.** Nearest-color-naming uses raw
  RGB distance, so very dark saturated colors (e.g. dark green in dim light) get
  misclassified as `black`. An HSV-based comparison would fix this but hasn't been
  built.
- **Single-pose assumption.** `PoseEstimator` requests `num_poses=1` and isn't
  cropped to a specific tracked person's bounding box — correct for this
  one-person clip, but would misattribute wrists in a multi-person scene.
- **Track ID churn on occlusion.** The centroid tracker drops a track after 5
  consecutive sampled frames with no matching detection; if the person reappears
  after a longer gap they get a new `PERSON_n` id rather than resuming the old one.
- **Hand-to-prop distance cap (800px) is empirically tuned**, not physically
  derived — set from the observed clean-frame range (174-656px) with headroom
  below the smallest observed bad estimate (1297px) on this specific clip's
  resolution (1440x2732). May need retuning for very different frame sizes.
- **No prop identity disambiguation.** If two same-type props (e.g. two wine
  glasses) appear in one frame, both get the same `name` with no index/id to
  tell them apart.
- **Prop list is hardcoded** to COCO `wine glass` and `cup` — anything else
  (bottles, other objects) isn't detected.

## Project structure

```
main.py                    CLI entry point, wires the pipeline together
service.py                 FastAPI wrapper over main.py for backend integration
src/
  frame_extractor.py       OpenCV frame sampling
  object_detector.py       YOLO wrapper (person + prop classes in one pass)
  coco_classes.py          COCO class-id constants
  nms.py                   Explicit greedy IoU dedup (on top of YOLO's own NMS)
  geometry.py               bbox center / screen-position (left/center/right)
  tracker.py                Centroid-based frame-to-frame person tracking
  pose_estimator.py         MediaPipe Pose wrapper, wrist extraction + bounds gate
  hand_association.py       Nearest-wrist prop association + distance gate
  movement.py               Bbox-center-delta movement classification
  costume.py                Dominant torso color estimate
  timecode.py               Seconds -> HH:MM:SS.mmm
  debug_draw.py              Debug visualization (boxes, wrists, prop centers)
```
