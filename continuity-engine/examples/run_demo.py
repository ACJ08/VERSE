"""End-to-end demo: the First Working Milestone from the plan.

    python examples/run_demo.py

Script says the glass is in Sarah's left hand; footage shows the right hand.
The engine stores both facts, links them to the same scene/character/prop,
flags the mismatch, and prints a report with sources and a suggested fix.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine import ContinuityEngine  # noqa: E402
from app.graph.storage import FactStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent


def main() -> None:
    script = json.loads((EXAMPLES / "script_scenes.json").read_text(encoding="utf-8"))
    footage = json.loads((EXAMPLES / "footage_observations.json").read_text(encoding="utf-8"))

    engine = ContinuityEngine(store=FactStore(":memory:"))
    engine.ingest_script(script)
    engine.ingest_footage(footage)

    print("graph:", engine.stats())

    report = engine.analyse("SCENE_012")
    print(f"\noverall score: {report.overall_score}")
    print("category scores:", report.category_scores)
    print("summary:", report.score_summary.main_reason)

    for issue in report.issues:
        print(f"\n[{issue.severity.value.upper()}] {issue.type} ({issue.category.value})")
        print(f"  entity      : {issue.entity.name}")
        expected_source = issue.expected.source.value if issue.expected.source else "n/a"
        observed_source = issue.observed.source.value if issue.observed.source else "n/a"
        print(f"  expected    : {issue.expected.value}  <- {expected_source}"
              f" ({issue.expected.source_reference})")
        print(f"  observed    : {issue.observed.value}  <- {observed_source}"
              f" ({issue.observed.source_reference})")
        print(f"  confidence  : {issue.confidence}")
        print(f"  score impact: -{issue.score_impact}")
        print(f"  explanation : {issue.explanation}")
        print(f"  fix         : {issue.suggested_fix}")

    if report.temporary_assumptions:
        print("\ntemporary assumptions:")
        for assumption in report.temporary_assumptions:
            print(f"  - {assumption.description} (confidence {assumption.confidence})")


if __name__ == "__main__":
    main()
