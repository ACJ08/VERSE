# Demo — stand-ins for the other four roles

Lets the full VERSE pipeline run today, before teams 1, 2, 4 and 5 deliver.
**Only the continuity engine is real.** Everything here is scaffolding to be
deleted as each team's work lands.

| Role | Stand-in | Replace with |
|---|---|---|
| 1 · Script & Granite | `mocks/script_extractor.py` — regex, no LLM | their Granite pipeline |
| 2 · Video Vision | `mocks/vision_detector.py` — no OpenCV | their detector output |
| 3 · **Continuity reasoning** | **`../continuity-engine/` — real** | — |
| 4 · Frontend | `dashboard.body.html` — static, no React | their Next.js dashboard |
| 5 · Backend | `server.py` — in-memory, single worker | their FastAPI service |

## Run it

```bash
python demo/pipeline.py          # full pipeline in the terminal, with verification
python demo/build_dashboard.py   # bake demo/dashboard.html
python demo/server.py            # http://127.0.0.1:8000
```

## Why the mock plants errors

`vision_detector.INJECTED_ERRORS` declares exactly which continuity errors the
"footage" contains. The pipeline then checks the engine found those and only
those. Without declared ground truth, a demo only proves the code *runs* — not
that the reasoning is right.

Currently planted:

| Scene | Character | Error | Should surface as |
|---|---|---|---|
| 012 | Sarah | hand left → right | `hand_mismatch`, softened by the panic beat |
| 013 | Sarah | hand left → right again | `hand_mismatch`, escalated to high |
| 013 | Sarah | blue blazer → red cardigan | `costume_mismatch`, unexplained |
| 013 | Marcus | frame right → frame left | `screen_direction_mismatch` |
| 015 | Marcus | notebook not detected | `missing_object` |

And three things that must **not** be flagged: scene 11 (agrees), scene 14's
costume change (the script says she removes the blazer), and any retroactive
excuse from a later scene's disturbance.

These checks run in CI too — `continuity-engine/tests/test_demo_pipeline.py`.

## Swapping a mock out

Each mock returns the JSON documented in
[../continuity-engine/docs/INTEGRATION.md](../continuity-engine/docs/INTEGRATION.md).
Point `pipeline.py` at the real source and delete the mock — the engine does
not know or care which produced the payload.
