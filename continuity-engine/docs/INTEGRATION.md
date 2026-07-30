# Integration guide

**For teams 1 (script), 2 (vision), 4 (frontend) and 5 (backend).**

The continuity engine is a plain Python package with an optional FastAPI
router. It has no database of its own beyond SQLite and no external service
dependencies.

---

## The short version: you no longer have to reshape anything

`app/adapters/` accepts each producing team's **native output** and reshapes it
to the contract below. Post your own response shape to
`POST /continuity/ingest-adapted/{script|footage|call_sheet|auto}` and you are
done:

| You send | Endpoint | What the adapter does |
|---|---|---|
| `AnalyseScriptResponse` (team 1) | `/continuity/ingest-adapted/script` | Lifts `metadata.scene_id`, maps `costume`/`position`/`hand_usage` onto compared attributes, re-homes `props[].owner` onto that character, keeps `continuity_notes` out of the fact stream |
| `scene_<id>.json` (team 2) | `/continuity/ingest-adapted/footage` | Aggregates per-frame detections into one statement per attribute per scene, with confidence scaled by frame agreement |
| `CallSheetResponse` (team 1) | `/continuity/ingest-adapted/call_sheet` | Expands scene numbers, strips call times off cast names |

Or use it as a library:

```python
from app.adapters import adapt_any
adapted = adapt_any(payload, entity_aliases={"PERSON_1": "Sarah"})
engine.ingest(adapted.payload, adapted.source)
print(adapted.warnings)   # things you should know about, e.g. unmapped track ids
```

The hand-shaped contract below still works and is still the thing the engine
speaks internally — read it to understand *why* the adapters do what they do,
and what makes a payload useful rather than merely accepted.

**Storing a fact is not the same as comparing it.** A fact only takes part in a
continuity check when it lands on an attribute a rule watches: `wears`, `holds`,
`held_in_hand`, `screen_position`, `movement`, `location`, `lighting`. Anything
else is stored, shown in the UI, and picked up only by the catch-all rule when
*both* sides happen to use the same novel attribute name.

---

## Team 1 — Script Intelligence & Granite

Send me nested JSON. **I do not require fixed field names.** Anything I don't
recognise becomes a fact anyway, and your original key is preserved on it.

```json
{
  "scenes": [
    {
      "scene_id": "SCENE_012",
      "sequence": 12,
      "location": "coffee shop",
      "action": "Sarah raises the glass. The crowd panics and rushes through the shop.",
      "characters": [
        { "name": "Sarah", "type": "character",
          "wears": "blue blazer", "holds": "glass", "held_in_hand": "left" }
      ],
      "props": [ { "name": "glass", "type": "prop", "location": "table" } ]
    }
  ]
}
```

What actually matters:

- **`scene_id`** on every scene — this is how I join your data to team 2's.
- **`sequence`** = screenplay order (not shooting order). I'll infer it from
  `SCENE_012` → 12 if you omit it, but send it if you have it.
- **`name`** on every entity. Without it I can't build an entity node.
- **`action` / `description`** free text — I mine this for explicit changes
  ("Sarah removes her blazer") and narrative assumptions ("the crowd panics").
  **This is high value; please include it.**
- Nesting depth is up to you. Metadata (`scene_id`, `confidence`, `timestamp`)
  is inherited by nested objects.

If your field names differ from mine, don't change your output — tell me and
I'll add an alias to `app/config/project_config.json`.

### What the adapter does with your response

`app/adapters/script_intelligence.py`, verified against
`examples/script_intelligence_response.json`:

- `metadata.scene_id` → the scene's `scene_id`; `sequence` inferred from it.
- `characters[].costume` → `wears`, `props[].hand_usage` → `held_in_hand`.
- `props[].owner` also becomes `holds` + `held_in_hand` **on that character**,
  which is what the props rules compare. Without an owner there is no
  character-level claim about who is holding what.
- **Prose stays off compared attributes.** `position: "standing by the door"` is
  not comparable to vision's `left`/`center`/`right`, so a screen side is only
  emitted when your text actually names one ("frame left", "camera right");
  otherwise the prose is kept as `blocking_description`, which vision never
  produces and so never conflicts. Same split for `movement` vs
  `movement_description`.
- `action` is read for scripted changes and narrative triggers. `raw_scene_text`
  is `exclude=True` in your schema so it never reaches me — **`action` is the
  field that matters**, and the script service now populates it with the scene's
  description prose (dialogue stripped).
- `continuity_notes` are returned to the UI as notes, never ingested as facts —
  they are your model's opinions, not observations of the production.
- `confidence_score` scales the weight of every fact from that scene.

---

## Team 2 — Video Vision

Same deal, plus per-detection confidence.

```json
{
  "observations": [
    {
      "scene_id": "SCENE_012",
      "sequence": 12,
      "timestamp": "00:14.2",
      "detections": [
        { "name": "Sarah", "type": "character", "confidence": 0.91,
          "wears": "navy jacket", "holds": "glass",
          "hand": "right", "position": "frame right" }
      ]
    }
  ]
}
```

- **`confidence`** (0–1) per detection. I scale score impact by it —
  low-confidence detections barely move the number, so please send honest
  values rather than rounding up.
- **`timestamp`** shows in the UI as the source reference. Include it.
- **`scene_id`** must match team 1's exactly.
- Free-text values are fine — I match "navy jacket" to "blue blazer".

### Send your per-frame document as-is

You do not need to aggregate anything before sending. Post the
`scene_<id>.json` your CLI writes, or use `POST /upload/footage`, and
`app/adapters/vision.py` handles it:

- **Frames collapse to one statement per attribute.** The modal value across
  frames wins. 55 frames of detections become ~9 observations.
- **Confidence reflects agreement.** It is the mean detector confidence for the
  frames backing the winning value, scaled by the share of reporting frames that
  agreed. A torso colour that reads black/pink/gray across the clip lands around
  0.24 and falls under `min_observation_confidence` — so detector flicker is
  recorded but does not become a wardrobe error. A stable value keeps its full
  confidence.
- **The first supporting frame's timestamp** is cited as the source reference.
- **Colour vs garment is not a mismatch.** Your `costume: "black"` against a
  script's `"black dress"` is the same claim at coarser resolution, and is
  scored as a match.

Two things only you can help with:

1. **`PERSON_n` needs a mapping.** Track ids share no tokens with script names,
   so pass `entity_aliases` (`{"PERSON_1": "Sarah"}`) with the payload — per
   request, or in the project's `entity_aliases` config table. Without it the
   footage lands on its own entities, and the engine then sees a scene that was
   shot with no sign of the props and wardrobe the script called for — which
   surfaces as false `missing_object` issues. The response `warnings` name the
   unmapped ids, so treat a warning there as "fix the mapping before trusting
   this report".
2. **`owner` is null in your output.** When a frame contains exactly one detected
   person and a prop associated to a wrist, the adapter attributes the prop to
   that person and emits `holds` / `held_in_hand` with
   `source: "ai_inference"` — compared, but trusted below direct detection. With
   two or more people in frame nothing is inferred. If you ever can attribute a
   prop yourself, send `owner` and it will be used at footage trust instead.

### Or let the backend call you

`vision_pipeline/service.py` wraps your CLI in FastAPI, so the backend can
process a clip a user uploaded through the dashboard:

```bash
cd vision_pipeline && uvicorn service:app --port 8200
# then, for the engine:
export VISION_SERVICE_URL=http://localhost:8200
```

`POST /upload/footage` with a video then forwards to your `/process`; with a
`.json` file it skips you entirely, so the engine needs none of your
dependencies installed.

---

## Team 5 — Backend Integration

### As a library

```python
from app.engine import ContinuityEngine
from app.graph.storage import FactStore

engine = ContinuityEngine(store=FactStore("verse.db"))
engine.ingest_script(script_json)
engine.ingest_footage(footage_json)
report = engine.analyse(scene_id="SCENE_012")   # or analyse() for all scenes
```

### As a router

```python
from app.api.routes import router
app.include_router(router)
```

| Method | Path | Purpose |
|---|---|---|
| POST | `/continuity/ingest/script` | Team 1 payload, already in engine shape |
| POST | `/continuity/ingest/footage` | Team 2 payload, already in engine shape |
| POST | `/continuity/ingest/{source}` | `human`, `call_sheet`, `ai_inference` |
| POST | `/continuity/ingest-adapted/{shape}` | **Producing team's native shape** — `script`, `footage`, `call_sheet` or `auto` |
| POST | `/continuity/pipeline/run` | Script + footage (+ call sheet) in one call, then analyse |
| POST | `/continuity/analyse` | Run analysis → `ContinuityReport` |
| GET | `/continuity/scenes/{project_id}` | Per-scene rollup + project overview |
| GET | `/continuity/entities/{project_id}` | Expected vs observed per entity attribute |
| GET | `/continuity/issues/{project_id}` | Current issues, no re-run |
| POST | `/continuity/feedback` | confirm / dismiss / resolve / reopen |
| POST | `/continuity/facts/override` | Human fact correction |
| GET | `/continuity/health` | Liveness |
| POST | `/upload/screenplay` | PDF/TXT/FDX → script service, or Granite, or regex |
| POST | `/upload/footage` | Vision `scene_<id>.json`, or a clip via the vision service |
| POST | `/upload/call-sheet` | Call-sheet document via the script service |

### Upstream services are optional

```bash
SCRIPT_SERVICE_URL=http://localhost:8100   # script-intelligence
VISION_SERVICE_URL=http://localhost:8200   # vision_pipeline/service.py
```

`/upload/screenplay` tries the script service, then watsonx Granite, then a
regex parser, and reports which ran in `extractor` plus why in `warnings`. An
offline sibling service degrades the extraction; it never fails the upload.

**Two things to fix before deployment:** `_ENGINES` in `api/projects.py` is a
process-local dict (breaks with multiple workers), and `FactStore` is SQLite —
swap in Postgres by reimplementing its interface.

Ingestion **is** deduplicated per project by payload hash, so a retried upload
returns `{"duplicate": true, "facts_ingested": 0}` rather than doubling every
fact. Call `analyse()` after ingesting, not per fact — or pass `analyse: true`
to the ingest and upload endpoints to get the report in the same response.

---

## Team 4 — Frontend

`POST /continuity/analyse` returns:

```json
{
  "project_id": "VERSE_DEMO",
  "scene_id": "SCENE_012",
  "overall_score": 91.3,
  "category_scores": { "props": 91.3, "costume": 100.0, "spatial": 91.3 },
  "issues": [
    {
      "issue_id": "ISSUE_A1B2C3D4",
      "category": "props",
      "type": "hand_mismatch",
      "severity": "medium",
      "confidence": 0.728,
      "entity": { "type": "character", "name": "Sarah", "key": "sarah" },
      "attribute": "held_in_hand",
      "scene_id": "SCENE_012",
      "expected": { "value": "left", "source": "script",
                    "source_reference": "Scene SCENE_012", "confidence": 1.0 },
      "observed": { "value": "right", "source": "footage",
                    "source_reference": "00:14.2", "confidence": 0.91 },
      "explanation": "The script places the item in sarah's left hand, ...",
      "suggested_fix": "Review the shot and move the item to the left hand ...",
      "status": "pending_review",
      "occurrences": 1,
      "related_scene_ids": ["SCENE_012"],
      "mitigated_by": ["ASSUM_1A2B3C4D"],
      "score_impact": 8.74
    }
  ],
  "temporary_assumptions": [
    { "assumption_id": "ASSUM_1A2B3C4D",
      "description": "Crowd disturbance may have moved objects ...",
      "confidence": 0.6, "source_text": "The crowd panics ..." }
  ],
  "score_summary": { "main_reason": "2 continuity issues reduced ...",
                     "penalties_applied": 2, "issues_mitigated": 2 }
}
```

Notes for the UI:

- **`expected.source` / `observed.source` may be `null`** — a `missing_object`
  issue has nothing observed to cite. Handle the null.
- **Scores are floats 0–100.** `score_impact` is what that issue subtracted.
- **`mitigated_by` non-empty** → show a "narrative context may explain this"
  badge; the score was already softened.
- **`occurrences` > 1** → the same error repeats across `related_scene_ids`,
  and severity has already escalated.
- **`status`** drives the review workflow. Send decisions to
  `POST /continuity/feedback` and re-run `analyse` to refresh scores.
- Filters worth building: category, severity, status, `scene_id`, confidence
  threshold.

### Two more reads for the screens the report cannot fill

`GET /continuity/scenes/{project_id}` — scene tracking, scene timeline, timeline
tracking:

```json
{
  "project_id": "VERSE_DEMO",
  "overview": { "scenes_total": 3, "scenes_shot": 1, "scenes_clean": 0,
                "issues_total": 1, "average_scene_score": 99.8,
                "facts": 63, "entities": 7, "categories_at_risk": ["movement"] },
  "scenes": [
    { "scene_id": "SCENE_001", "sequence": 1, "location": "COFFEE SHOP",
      "time_of_day": "DAY", "slugline": "INT. COFFEE SHOP - DAY",
      "score": 99.8, "category_scores": { "movement": 98.2 },
      "issue_count": 1, "issues_by_severity": { "low": 1 },
      "categories": ["movement"], "entities": [ { "type": "character", "name": "SARAH", "key": "sarah" } ],
      "sources": ["footage", "script"], "has_footage": true,
      "fact_count": 21, "headline": "Low: movement mismatch" }
  ]
}
```

- **`has_footage: false`** means the scene has not been shot, not that it is
  clean — `headline` says "Not shot yet — script only." Don't show a green 100%.
- Scenes are in **screenplay order** (`sequence`), never shooting order.
- A scene's `score` is computed with the same scorer as the project's, so the two
  cannot disagree.

`GET /continuity/entities/{project_id}?entity_type=character&attribute=wears` —
costume tracking, prop tracking, production memory, verification checklist:

```json
[
  { "entity": { "type": "character", "name": "SARAH", "key": "sarah" },
    "scene_ids": ["SCENE_001", "SCENE_002"],
    "attributes": ["held_in_hand", "holds", "screen_position", "wears"],
    "issue_count": 1, "conflict_count": 3, "fact_count": 26,
    "latest": { "wears": "black dress", "held_in_hand": "right" },
    "slots": [
      { "entity": { "type": "character", "name": "SARAH", "key": "sarah" },
        "attribute": "wears", "scene_id": "SCENE_001", "state": "conflict",
        "expected": { "value": "black dress", "source": "script",
                      "source_reference": "Scene SCENE_001", "confidence": 0.95 },
        "observed": { "value": "pink", "source": "footage",
                      "source_reference": "00:00:01.440", "confidence": 0.236 },
        "issue_id": null, "severity": null,
        "human_confirmed": false, "flagged": false } ] }
]
```

`state` is the field to render on:

| `state` | Meaning | Suggested label |
|---|---|---|
| `match` | Script and footage agree | Verified |
| `conflict` + `flagged: true` | Disagree, and the engine raised an issue | Mismatch |
| `conflict` + `flagged: false` | Disagree, but confidence was too low to penalise | Differs — low confidence |
| `unverified` | Expected, nothing observed yet | Awaiting footage |
| `observed_only` | Footage saw something the script never stated | Unscripted |

`flagged: false` on a conflict is not a bug: the engine records the disagreement
without scoring it, because acting on a 0.24-confidence detection wastes a
supervisor's time. Colour it as a warning, not an error.

Both endpoints, plus the upload and pipeline calls, are wrapped in
`src/app/lib/api.ts` (`continuity.scenes`, `continuity.entities`,
`continuity.runPipeline`, `upload.footage`) with hooks in
`src/app/lib/hooks.ts` (`useSceneViews`, `useEntityViews`, `useFootageUpload`).

---

## Changing the contract

`app/models/schemas.py` and `app/api/routes.py` are consumed by everyone.
Adding fields is safe. Renaming or removing them is not — raise it with the
team and update this file first.
