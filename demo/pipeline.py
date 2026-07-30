"""Full VERSE pipeline with demo stand-ins for teams 1, 2, 4 and 5.

    python demo/pipeline.py

Screenplay text -> mock Granite extraction -> mock vision detection ->
continuity engine -> report. Verifies the engine found the errors that the
mock detector deliberately planted.

Only the continuity engine here is real. Swap the mocks out as teams deliver.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "continuity-engine"))
sys.path.insert(0, str(ROOT))

from app.engine import ContinuityEngine  # noqa: E402
from app.graph.storage import FactStore  # noqa: E402
from app.models.schemas import FeedbackAction  # noqa: E402
from demo.mocks import script_extractor, vision_detector  # noqa: E402

SCREENPLAY = Path(__file__).resolve().parent / "screenplay.txt"

BOLD, DIM, RED, YELLOW, GREEN, CYAN, RESET = (
    "\033[1m", "\033[2m", "\033[31m", "\033[33m", "\033[32m", "\033[36m", "\033[0m"
)
_SEVERITY_COLOUR = {"low": DIM, "medium": YELLOW, "high": RED, "critical": RED}


def build_engine() -> tuple[ContinuityEngine, dict[str, Any], dict[str, Any]]:
    """Run the mock upstream teams and ingest their output."""
    script_json = script_extractor.extract_file(SCREENPLAY)
    footage_json = vision_detector.detect(script_json)

    engine = ContinuityEngine(store=FactStore(":memory:"))
    engine.ingest_script(script_json, extractor="mock-granite")
    engine.ingest_footage(footage_json, extractor="mock-vision")
    return engine, script_json, footage_json


def _header(text: str) -> None:
    print(f"\n{BOLD}{text}{RESET}\n" + "-" * len(text))


def main() -> None:
    engine, script_json, footage_json = build_engine()

    _header("1. Script extraction (mock team 1)")
    for scene in script_json["scenes"]:
        names = ", ".join(c["name"] for c in scene["characters"])
        print(f"  {scene['scene_id']}  {scene['location']:<12} characters: {names or '-'}")

    _header("2. Vision detection (mock team 2)")
    for observation in footage_json["observations"]:
        detected = ", ".join(
            f"{d['name']} ({d['confidence']:.2f})" for d in observation["detections"]
        )
        print(f"  {observation['scene_id']}  @{observation['timestamp']}  {detected}")

    _header("3. Knowledge graph")
    stats = engine.stats()
    print(f"  {stats['facts']} facts · {stats['entities']} entities · "
          f"{stats['scenes']} scenes · {stats['nodes']} nodes / {stats['edges']} edges")

    _header("4. Continuity analysis")
    report = engine.analyse()
    colour = GREEN if report.overall_score >= 90 else YELLOW if report.overall_score >= 70 else RED
    print(f"  overall: {colour}{BOLD}{report.overall_score}{RESET}/100")
    for category, score in sorted(report.category_scores.items()):
        if score < 100:
            print(f"    {category:<10} {score:>6.1f}")
    print(f"  {DIM}{report.score_summary.main_reason}{RESET}")

    _header(f"5. Issues found ({len(report.issues)})")
    for issue in sorted(report.issues, key=lambda i: -i.score_impact):
        tone = _SEVERITY_COLOUR[issue.severity.value]
        badge = " [mitigated]" if issue.mitigated_by else ""
        repeat = f" [x{issue.occurrences}]" if issue.occurrences > 1 else ""
        print(f"\n  {tone}{issue.severity.value.upper():<8}{RESET} "
              f"{CYAN}{issue.type}{RESET} · {issue.scene_id} · "
              f"{issue.entity.name}{badge}{repeat}")
        print(f"    expected {issue.expected.value!r} ({_src(issue.expected)})  ->  "
              f"observed {issue.observed.value!r} ({_src(issue.observed)})")
        print(f"    confidence {issue.confidence:.2f} · score impact -{issue.score_impact}")
        print(f"    {DIM}{issue.suggested_fix}{RESET}")

    _header("6. Did the engine catch what the mock planted?")
    caught, missed = _verify(report)
    for line in caught:
        print(f"  {GREEN}FOUND  {RESET} {line}")
    for line in missed:
        print(f"  {RED}MISSED {RESET} {line}")

    suppressed = _suppression_checks(report)
    _header("7. False-positive suppression")
    for label, ok, detail in suppressed:
        mark = f"{GREEN}OK    {RESET}" if ok else f"{RED}FAIL  {RESET}"
        print(f"  {mark} {label}\n         {DIM}{detail}{RESET}")

    _header("8. Human-in-the-loop (mock team 4 dashboard action)")
    target = next((i for i in report.issues if i.mitigated_by), report.issues[0])
    print(f"  dismissing {target.type} in {target.scene_id} as intentional...")
    engine.apply_feedback(
        FeedbackAction(issue_id=target.issue_id, action="dismiss", note="Director's choice.")
    )
    rerun = engine.analyse()
    print(f"  issues: {len(report.issues)} -> {len(rerun.issues)}   "
          f"score: {report.overall_score} -> {rerun.overall_score}")

    print(f"\n{BOLD}Done.{RESET} {len(missed)} planted errors missed, "
          f"{sum(1 for _, ok, _ in suppressed if not ok)} suppression checks failed.\n")

    if missed or any(not ok for _, ok, _ in suppressed):
        sys.exit(1)


def _src(ref) -> str:
    if ref.source is None:
        return "not observed"
    return f"{ref.source.value} {ref.source_reference}".strip()


def _verify(report) -> tuple[list[str], list[str]]:
    """Check every planted error produced an issue on the right entity/scene."""
    caught, missed = [], []
    for planted in vision_detector.expected_findings():
        label = (f"{planted['scene_id']} {planted['character']} "
                 f"{planted['attribute']} -> {planted['injected']}")
        hit = any(
            issue.scene_id == planted["scene_id"]
            and issue.entity.name.lower() == planted["character"].lower()
            and (issue.attribute == planted["attribute"] or planted["injected"] == "<removed>")
            for issue in report.issues
        )
        (caught if hit else missed).append(label)
    return caught, missed


def _suppression_checks(report) -> list[tuple[str, bool, str]]:
    """The engine must stay quiet where the script explains the change."""
    types_by_scene = {(i.scene_id, i.attribute) for i in report.issues}
    return [
        (
            "Explicit costume change is not flagged",
            ("SCENE_014", "wears") not in types_by_scene,
            "Scene 14: 'Sarah removes her blue blazer' justifies the grey shirt.",
        ),
        (
            "Matching scenes produce no issues",
            ("SCENE_011", "held_in_hand") not in types_by_scene,
            "Scene 11: script and footage agree, so nothing should be raised.",
        ),
        (
            "Narrative chaos softens the score impact",
            any(i.mitigated_by for i in report.issues),
            "Scene 12: 'the crowd panics' reduces the penalty without hiding the issue.",
        ),
    ]


def export_report(path: Path) -> dict[str, Any]:
    """Write the report as JSON — used by the dashboard and the server."""
    engine, script_json, footage_json = build_engine()
    report = engine.analyse()
    payload = {
        "report": json.loads(report.model_dump_json()),
        "script": script_json,
        "footage": footage_json,
        "stats": engine.stats(),
        "planted_errors": vision_detector.expected_findings(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    main()
