# Integration guide

**For teams 1 (script), 2 (vision), 4 (frontend) and 5 (backend).**

The continuity engine is a plain Python package with an optional FastAPI
router. It has no database of its own beyond SQLite and no external service
dependencies.

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
| POST | `/continuity/ingest/script` | Team 1 payload |
| POST | `/continuity/ingest/footage` | Team 2 payload |
| POST | `/continuity/ingest/{source}` | `human`, `call_sheet`, `ai_inference` |
| POST | `/continuity/analyse` | Run analysis → `ContinuityReport` |
| GET | `/continuity/issues/{project_id}` | Current issues, no re-run |
| POST | `/continuity/feedback` | confirm / dismiss / resolve / reopen |
| POST | `/continuity/facts/override` | Human fact correction |
| GET | `/continuity/health` | Liveness |

**Two things to fix before deployment:** `_ENGINES` in `api/routes.py` is a
process-local dict (breaks with multiple workers), and `FactStore` is SQLite —
swap in Postgres by reimplementing its interface.

Ingestion is idempotent per payload but **not** deduplicated across repeated
sends of the same payload. Call `analyse()` after ingesting, not per fact.

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

---

## Changing the contract

`app/models/schemas.py` and `app/api/routes.py` are consumed by everyone.
Adding fields is safe. Renaming or removing them is not — raise it with the
team and update this file first.
