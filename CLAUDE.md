# VERSE — working notes

Continuity intelligence for non-linear film production. Five engineers; this
repo currently holds **team 3's** work only.

**My scope (team 3): continuity reasoning & agent workflow.** Everything lives
in [continuity-engine/](continuity-engine/). I do not write script extraction,
vision, frontend or deployment code — I define the JSON contracts those teams
hand me and consume them.

## Read these first, not the whole tree

| File | What it holds |
|---|---|
| [continuity-engine/docs/CONTEXT.md](continuity-engine/docs/CONTEXT.md) | Architecture, data flow, key decisions |
| [continuity-engine/docs/PROGRESS.md](continuity-engine/docs/PROGRESS.md) | Phase status, what's next, known gaps |
| [continuity-engine/docs/INTEGRATION.md](continuity-engine/docs/INTEGRATION.md) | The contract other teams code against |

Update `PROGRESS.md` when a phase moves. Update `INTEGRATION.md` **before**
changing anything in `app/models/schemas.py` or `app/api/routes.py` — other
teams build against those.

## Commands

```bash
cd continuity-engine
python -m pytest              # 47 tests, all must pass
python examples/run_demo.py   # end-to-end milestone demo
```

## Working rules

- **Contracts are load-bearing.** `app/models/schemas.py` and `app/api/routes.py`
  are consumed by teams 1, 2, 4 and 5. Additive changes are fine; renames and
  removals need a note in `INTEGRATION.md` and a heads-up to the team.
- **Never depend on fixed field names from teams 1 and 2.** Their JSON will
  change. Add an alias to `app/config/project_config.json` instead of a branch
  in the parser.
- **New continuity checks go in `app/reasoning/rules.py`** via the `@rule`
  decorator. Do not edit the detector to add a check.
- **Tuning belongs in config, not code.** Trust levels, weights, penalties and
  thresholds all live in `project_config.json`.
- **Every rule needs a test**, plus a negative test proving it stays quiet when
  it should. False positives are the main risk to this product — a supervisor
  who stops trusting the flags gets no value from the tool.
- **Run the demo, not just the tests, after reasoning changes.** Three real bugs
  (substring trigger matching, double-counted mitigation, double-counted trust)
  showed up in demo output while all tests were green.
- Prefer editing an existing module over adding one. The folder layout mirrors
  the plan's phases and other teams navigate by it.
