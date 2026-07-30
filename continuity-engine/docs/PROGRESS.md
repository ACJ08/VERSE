# Progress

Living status doc. Update when a phase moves; keep it short.

**Last updated:** 2026-07-30 · **Tests:** 133 passing · **Demos:** both working

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
| 8 | Integration | ✅ Done | Adapters for teams 1 + 2, upload + pipeline endpoints, dashboard views, frontend wired |

## Plan test cases — all 15 covered

1 ✅ · 2 ✅ · 3 ✅ · 4 ✅ · 5 ✅ · 6 ✅ · 7 ✅ · 8 ✅ · 9 ✅ · 10 ✅ · 11 ✅ · 12 ✅ · 13 ✅ · 14 ✅ · 15 ✅

Plus regressions for the three bugs found in demo output (see CONTEXT.md) and the
four found running real team 1/2 payloads through the pipeline (see Log).

## Known gaps

- **No LLM anywhere in this package.** Entity matching, explanations and
  suggestions all use the rule-based path. Hooks exist (`llm=`,
  `SemanticMatcher`) and `services/watsonx.py` implements them, but no
  credentials have been exercised. Screenplay extraction *does* now reach
  Granite when `SCRIPT_SERVICE_URL` points at team 1's service.
- **Assumption triggers are a hand-written keyword table.** Fine for the demo,
  will miss real screenplay phrasing. Needs the LLM path.
- **Tuning is still guesswork.** Penalties, thresholds and trust levels have
  never been validated against footage a human has scored. Running the real
  vision clip through it suggests `min_observation_confidence` (0.35) and
  `min_conflict_confidence` (0.4) are roughly right for 2 fps sampling — most
  detector flicker lands below them, and the one flagged issue was real — but
  that is one clip, not calibration.
- **Identity resolution is manual.** `entity_aliases` maps `PERSON_1` → `Sarah`
  per clip, and track-id churn means the mapping is not stable across a scene.
  Embeddings or face clustering would fix it properly.
- **Prop-holder inference is single-person only.** Two people in frame and the
  adapter declines to guess who holds the glass, so the character-level hand
  check silently does not run for crowd scenes.
- **`_ENGINES` in `api/projects.py` is a process-local dict.** Fine for the demo,
  wrong for multi-worker deployment.
- **Only equality-style comparison.** No numeric tolerances (e.g. "roughly
  centre frame"), no time-based reasoning within a scene. Screen position is
  coarse: left/centre/right only.

## Next

1. Wire the LLM hooks once team 1's watsonx credentials exist — assumption
   triggers first, they are the weakest rule-based component.
2. Re-tune scoring against a scene a human has continuity-scored by hand.
3. Replace manual `entity_aliases` with embedding-based identity resolution.
4. Swap `FactStore` for Postgres and `_ENGINES` for a shared cache before any
   multi-worker deployment.

## Log

- **2026-07-21** — Scaffold built. All 8 phases have working code, 47 tests
  pass, milestone demo runs. Fixed three bugs found via demo output: substring
  trigger matching ("window" → "wind"), double-counted assumption mitigation,
  double-counted source trust in scoring.
- **2026-07-30** — Pipeline connected end to end: `app/adapters/` for teams 1
  and 2, `services/pipeline.py` for the upstream service calls,
  `reporting/views.py` for the scene and entity reads, upload endpoints for
  screenplays/footage/call sheets, and the frontend pages wired to all of it.
  86 new tests, fixtures in every producer's real shape.

  Four bugs surfaced by running actual team 1/2 payloads through it:

  1. **`_note` keys in `project_config.json` poisoned the alias tables.** A
     documentation string was iterated character by character, so every single
     letter became an alias — `keyword_semantic_matcher` then scored *any* two
     names at 0.9 and merged every character into one entity. Went unnoticed
     because the demo fixture has one character. Filtered in the config
     accessors.
  2. **Naive substring matching in `keyword_semantic_matcher`.** The one-letter
     hand shorthands ("l", "r") matched almost anything — "SARAH" and "PERSON_2"
     both contain an "r". Now whole-word, with short terms requiring equality.
  3. **Enumerated names merged.** "SCENE_011"/"SCENE_012" and
     "PERSON_2"/"PERSON_3" score ~0.88 on string similarity, so distinct scenes
     and distinct tracked people collapsed into single nodes. Scene entities no
     longer fuzzy-match at all, and members of a numbered series are excluded.
  4. **Envelope keys became facts.** A top-level `project_id` produced a fact on
     a phantom `unknown_scene` entity, and every `type: "character"` produced a
     `type` fact. Both are metadata the parser already consumes; now skipped.

  Also: vision's torso *colour* ("black") was scored as a costume mismatch
  against the script's *garment* ("black dress"). `values_match` now treats one
  value's tokens being a subset of the other's as agreement — the same claim at
  coarser resolution is not a continuity error.
