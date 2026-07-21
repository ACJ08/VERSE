# Progress

Living status doc. Update when a phase moves; keep it short.

**Last updated:** 2026-07-21 · **Tests:** 47 passing · **Demo:** working

## Phases

| # | Phase | Status | Notes |
|---|---|---|---|
| 1 | Contracts & mock data | ✅ Done | `schemas.py`, `examples/`, `project_config.json` |
| 2 | Dynamic ingestion | ✅ Done | Nested JSON, aliases, unknown fields, raw labels kept |
| 3 | Knowledge graph | ✅ Done | NetworkX + timeline + SQLite |
| 4 | Rule-based comparison | ✅ Done | 8 rules incl. custom-attribute catch-all |
| 5 | Natural-language reasoning | 🟡 Partial | Rule-based only — **no LLM wired yet** |
| 6 | Scoring & reporting | ✅ Done | Category + overall, explanations, fixes |
| 7 | Human feedback | ✅ Done | Confirm/dismiss/override, history preserved |
| 8 | Integration | 🟡 Partial | Router built; **not yet tested against real team data** |

## Plan test cases — all 15 covered

1 ✅ · 2 ✅ · 3 ✅ · 4 ✅ · 5 ✅ · 6 ✅ · 7 ✅ · 8 ✅ · 9 ✅ · 10 ✅ · 11 ✅ · 12 ✅ · 13 ✅ · 14 ✅ · 15 ✅

Plus regressions for the three bugs found in demo output (see CONTEXT.md).

## Known gaps

- **No LLM anywhere.** Entity matching, explanations and suggestions all use
  the rule-based path. Hooks exist (`llm=`, `SemanticMatcher`) but nothing is
  connected to watsonx/Granite.
- **Assumption triggers are a hand-written keyword table.** Fine for the demo,
  will miss real screenplay phrasing. Needs the LLM path.
- **Tuning is guesswork.** Penalties, thresholds and trust levels have never
  been validated against footage a human has scored. Expect to re-tune once
  real data arrives.
- **`_ENGINES` in `api/routes.py` is a process-local dict.** Fine for the demo,
  wrong for multi-worker deployment — team 5 should replace it.
- **Only equality-style comparison.** No numeric tolerances (e.g. "roughly
  centre frame"), no time-based reasoning within a scene.

## Next

1. Send `docs/INTEGRATION.md` to teams 1, 2 and 5; agree on the JSON shapes.
2. Run the parser against the first real Granite and vision outputs, fix what
   breaks, add fixtures from real payloads to `examples/`.
3. Wire the LLM hooks once team 1's watsonx credentials exist.
4. Re-tune scoring against a scene a human has continuity-scored by hand.

## Log

- **2026-07-21** — Scaffold built. All 8 phases have working code, 47 tests
  pass, milestone demo runs. Fixed three bugs found via demo output: substring
  trigger matching ("window" → "wind"), double-counted assumption mitigation,
  double-counted source trust in scoring.
