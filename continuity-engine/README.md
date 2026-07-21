# VERSE Continuity Engine

Team 3 — continuity reasoning & agent workflow.

Compares what the script *expected* against what the footage *observed*, flags
mismatches with sources and confidence, scores the result, and keeps a human in
charge of every decision.

## Quick start

```bash
cd continuity-engine
pip install -r requirements.txt
python -m pytest                # 47 tests
python examples/run_demo.py     # end-to-end demo
```

## Use it

```python
from app.engine import ContinuityEngine

engine = ContinuityEngine()
engine.ingest_script(script_json)      # team 1
engine.ingest_footage(footage_json)    # team 2
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
├── ingestion/        JSON -> facts
├── graph/            timeline, memory, storage
├── reasoning/        rules, assumptions, detection
├── scoring/          category + overall scores
├── reporting/        explanations, suggested fixes
├── feedback/         human-in-the-loop
└── api/              FastAPI router
docs/                 CONTEXT · PROGRESS · INTEGRATION
examples/             mock data + demo
tests/                47 tests
```

## Docs

- [docs/INTEGRATION.md](docs/INTEGRATION.md) — **other teams start here**
- [docs/CONTEXT.md](docs/CONTEXT.md) — architecture and decisions
- [docs/PROGRESS.md](docs/PROGRESS.md) — status and known gaps
