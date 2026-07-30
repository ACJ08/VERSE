# Architecture & decisions

Stable reference. Read this instead of re-reading the source tree.

## Data flow

```
Screenplay ─> Script service (team 1) ─┐
Video clip ─> Vision service (team 2) ─┼─> Adapters ─> DynamicParser ─> Fact[] ─┐
Call sheets / human notes ─────────────┘                                        │
                                                                                v
                                              KnowledgeGraph ─> ProductionMemory
                                                     │                  │
                                              Timeline (screenplay order)
                                                                        │
                                AssumptionEngine ─> ConflictDetector <───┘
                                                           │
                                                       Issue[]
                                                           │
                                 CategoryScorer ─> Explanations ─> Suggestions
                                                           │
                                                  ContinuityReport ──┐
                                                                     ├─> dashboard
                                    SceneView[] / EntityView[] ──────┘
```

The adapters are the layer that makes the two producing pipelines comparable
rather than merely storable, and the two view builders answer the questions the
report does not: "what is this scene?" and "what do we currently believe about
this character?".

## Module map

| Module | Responsibility |
|---|---|
| `app/engine.py` | **The facade.** Other teams only need this. |
| `app/models/schemas.py` | Shared contracts. Changing these breaks other teams. |
| `app/config/` | All tunables: trust, weights, penalties, thresholds, aliases. |
| `app/adapters/` | Producing teams' native payloads → engine payloads. |
| `app/services/pipeline.py` | Upstream service clients + ingest orchestration. |
| `app/reporting/views.py` | Scene and entity read models for the dashboard. |
| `app/ingestion/dynamic_parser.py` | Arbitrary nested JSON → `Fact[]`. |
| `app/ingestion/normaliser.py` | Field/value canonicalisation + similarity. |
| `app/ingestion/entity_matcher.py` | "Sarah" == "SARAH". AI hook for embeddings. |
| `app/graph/builder.py` | NetworkX graph + fact index. |
| `app/graph/timeline.py` | Screenplay order and narrative proximity. |
| `app/graph/memory.py` | Trust-resolved expected vs observed per slot. |
| `app/graph/storage.py` | SQLite persistence. |
| `app/reasoning/rules.py` | The checks. **Extension point.** |
| `app/reasoning/assumptions.py` | Explicit changes + temporary assumptions. |
| `app/reasoning/conflict_detector.py` | Runs rules, suppresses, escalates. |
| `app/scoring/` | Category and overall scores. |
| `app/reporting/` | Explanations and suggested fixes (LLM-optional). |
| `app/feedback/human_feedback.py` | Human decisions and fact overrides. |
| `app/api/routes.py` | FastAPI router for team 5 to mount. |

## Key decisions

**Facts are never overwritten.** Conflicting claims coexist in the graph;
resolution happens at comparison time -via trust. Losing the losing value would
make the "expected vs observed with sources" UI impossible.

**Trust vs confidence are separate axes.** Trust = how much we believe the
*source type* (human > script > call sheet > footage > AI). Confidence = how
sure that source was about this specific observation. `Fact.weight` combines
them; human-confirmed facts short-circuit to 1.0.

**Expectations carry forward across scenes.** If the script says nothing new
about Sarah's jacket in scene 12, scene 11's statement still governs. Continuity
errors are mostly about state persisting when it shouldn't have changed.

**Rules are a registry, not a chain of ifs.** `@rule(...)` registers a check.
The detector handles suppression, escalation and issue construction once, so
every rule gets that behaviour for free.

**Suppression is layered, and each layer applies exactly once:**
1. Explicit scripted change ("Sarah removes her blazer") → issue cancelled.
2. Temporary assumption (panic, fight, storm) → score impact reduced.
3. Dismissed pattern → suppressed on all future runs.

Severity reflects the *error type* plus repetition. It deliberately does **not**
drop for mitigation — applying mitigation to both severity and score impact
discounted justified issues twice and made them vanish.

**LLMs are optional everywhere.** `ExplanationWriter` and `SuggestionWriter`
take an optional `LanguageModel`; rule-based text is always the fallback, and
LLM exceptions are swallowed. A report never fails because watsonx is down.

**Scoring counts belief once.** `issue.confidence` (from `rules._confidence`)
already folds in source trust, observation confidence and narrative proximity.
The scorer must not re-multiply by trust.

**Adapters aggregate footage per scene, not per frame.** Vision samples at 2 fps,
so a 30-second clip is ~60 observations of the same state. Ingesting them
individually would emit dozens of competing facts per attribute and turn detector
noise (a torso colour reading black, then pink, then gray) into continuity
errors. The modal value wins and its confidence is scaled by the share of
reporting frames that agreed, so flicker survives as a low-confidence record
instead of a false alarm.

**Prose and enums are different kinds of claim.** A screenplay says "crosses to
the window"; vision says "moving". Only values from the same vocabulary are
allowed onto a compared attribute — script prose that names no screen side or
movement state is kept on `blocking_description` / `movement_description`, which
vision never produces and therefore never conflicts with. The alternative,
comparing prose to enums, generates issues no human would call errors.

**A less detailed statement is not a contradiction.** Vision reports a torso
colour ("black") where the script describes a garment ("black dress").
`values_match` treats one value's tokens being a subset of the other's as
agreement, so coarser observation is not scored as a wardrobe change.

**Adapter-derived claims declare weaker provenance.** When the adapter infers
which character holds a prop (one person in frame, prop associated to a wrist) it
emits the fact with `source: "ai_inference"`, not `footage`. The trust model then
does the right thing without the reasoning layer needing to know an inference
happened.

**Derived views recompute, never store.** `SceneView` and `EntityView` are built
from the graph and memory on request, and scene scores go through the same
`CategoryScorer` the report uses — a scene's score cannot drift from the
project's because there is only one scorer.

## Extension points for teammates

| Want to... | Do this |
|---|---|
| Add a continuity check | `@rule(...)` in `app/reasoning/rules.py` |
| Handle a new field name | Add an alias in `project_config.json` |
| Support a new producer shape | Add a module in `app/adapters/`, register it in `detect_shape` |
| Join vision ids to script names | `entity_aliases`, per request or in `project_config.json` |
| Add a dashboard read model | Build it in `app/reporting/views.py` from graph + memory |
| Add a narrative trigger | Extend `_TRIGGERS` in `assumptions.py` |
| Swap in a real LLM | Pass `llm=` to `ContinuityEngine` |
| Swap in embeddings | Pass a `SemanticMatcher` to `EntityMatcher` |
| Use Postgres | Reimplement `FactStore`'s interface |
