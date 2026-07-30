# VERSE Continuity Engine

Team 3 — continuity reasoning & agent workflow.

Compares what the script *expected* against what the footage *observed*, flags
mismatches with sources and confidence, scores the result, and keeps a human in
charge of every decision.

## Quick start

```bash
cd continuity-engine
pip install -r requirements.txt
python -m pytest                        # 133 tests
python examples/run_demo.py             # engine-contract demo
python examples/run_pipeline_demo.py    # full pipeline: team 1 + team 2 payloads -> report
```

`run_pipeline_demo.py` is the one to look at first: it takes the real payload
shapes the script and vision pipelines emit, adapts them, ingests them, and
prints the report plus the two views the dashboard renders. No credentials and no
running services needed.

## Use it

```python
from app.adapters import adapt_script_intelligence, adapt_vision
from app.engine import ContinuityEngine

engine = ContinuityEngine()

# Producing teams' own shapes — the adapters land their fields on the attributes
# the rules compare, and aggregate vision's per-frame output per scene.
engine.ingest_script(adapt_script_intelligence(script_service_response).payload)
engine.ingest_footage(
    adapt_vision(vision_scene_document, entity_aliases={"PERSON_1": "Sarah"}).payload
)

report = engine.analyse("SCENE_012")

print(report.overall_score)            # 91.3
for issue in report.issues:
    print(issue.type, issue.expected.value, "->", issue.observed.value)
```

Serve it:

```python
from fastapi import FastAPI
from app.api.routes import router

app = FastAPI()
app.include_router(router)             # uvicorn app.main:app --reload
```

## What it detects

`hand_mismatch` · `prop_mismatch` · `missing_object` · `costume_mismatch` ·
`movement_mismatch` · `screen_direction_mismatch` · `location_mismatch` ·
`lighting_mismatch` · `custom_attribute_conflict`

The last one is a catch-all, so attributes nobody anticipated still get checked.

## Add a check

```python
from app.reasoning.rules import rule, RuleContext, RuleResult
from app.models.schemas import Category, Severity

@rule(id="umbrella_state", category=Category.PROPS, attributes=["umbrella_state"])
def umbrella(ctx: RuleContext) -> RuleResult | None:
    slot = ctx.slot
    if not slot.has_conflict_candidates:
        return None
    if ctx.normaliser.values_match(slot.expected.value, slot.observed.value):
        return None
    return RuleResult(
        rule_id="umbrella_state",
        category=Category.PROPS,
        severity=Severity.LOW,
        confidence=0.8,
        explanation=f"Umbrella expected {slot.expected.value}, observed {slot.observed.value}.",
    )
```

Suppression, escalation, scoring and reporting come for free.

## Tune it

Everything adjustable lives in [app/config/project_config.json](app/config/project_config.json):
trust levels, category weights, severity penalties, confidence thresholds,
field aliases, value synonyms, assumption lifetimes.

## Layout

```
app/
├── engine.py         facade — start here
├── models/           shared contracts
├── config/           all tunables
├── adapters/         producing-team payloads -> engine payloads
├── ingestion/        JSON -> facts
├── graph/            timeline, memory, storage
├── reasoning/        rules, assumptions, detection
├── scoring/          category + overall scores
├── reporting/        explanations, suggested fixes, dashboard views
├── feedback/         human-in-the-loop
├── services/         watsonx + upstream service clients
└── api/              FastAPI routers (continuity, upload, auth, projects)
docs/                 CONTEXT · PROGRESS · INTEGRATION
examples/             fixtures in every producer's shape + two demos
tests/                133 tests
```

## Docs

- [docs/INTEGRATION.md](docs/INTEGRATION.md) — **other teams start here**
- [docs/CONTEXT.md](docs/CONTEXT.md) — architecture and decisions
- [docs/PROGRESS.md](docs/PROGRESS.md) — status and known gaps
