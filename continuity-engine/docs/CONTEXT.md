# Architecture & decisions

Stable reference. Read this instead of re-reading the source tree.

## Data flow

```
Script JSON (team 1) ─┐
Footage JSON (team 2) ─┼─> DynamicParser ─> Fact[] ─> KnowledgeGraph ─> ProductionMemory
Call sheets / human ──┘                                     │                  │
                                                     Timeline (screenplay order)
                                                                               │
                                       AssumptionEngine ─> ConflictDetector <──┘
                                                                  │
                                                              Issue[]
                                                                  │
                                        CategoryScorer ─> Explanations ─> Suggestions
                                                                  │
                                                        ContinuityReport ─> teams 4/5
```

## Module map

| Module | Responsibility |
|---|---|
| `app/engine.py` | **The facade.** Other teams only need this. |
| `app/models/schemas.py` | Shared contracts. Changing these breaks other teams. |
| `app/config/` | All tunables: trust, weights, penalties, thresholds, aliases. |
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
resolution happens at comparison time via trust. Losing the losing value would
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

## Extension points for teammates

| Want to... | Do this |
|---|---|
| Add a continuity check | `@rule(...)` in `app/reasoning/rules.py` |
| Handle a new field name | Add an alias in `project_config.json` |
| Add a narrative trigger | Extend `_TRIGGERS` in `assumptions.py` |
| Swap in a real LLM | Pass `llm=` to `ContinuityEngine` |
| Swap in embeddings | Pass a `SemanticMatcher` to `EntityMatcher` |
| Use Postgres | Reimplement `FactStore`'s interface |
