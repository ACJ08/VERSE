"""End-to-end demo of the connected ingestion pipeline.

    python examples/run_pipeline_demo.py

Runs the real payload shapes the other two teams emit — team 1's
`AnalyseScriptResponse` and team 2's per-frame vision document — through the
adapters, the engine, and the derived views the dashboard reads. No credentials,
no running services, no vision dependencies required.

What it demonstrates:

1. Team 1's nested `metadata.scene_id` shape is reshaped so its fields land on
   the attributes the continuity rules actually compare.
2. Team 2's 8 frames of flickering per-frame detections collapse into one
   statement per attribute, with confidence scaled by how many frames agreed.
3. `entity_aliases` is what joins "PERSON_1" to "SARAH". Run with
   `--no-aliases` to see what happens without it: the footage lands on its own
   entities, so the engine sees a scene that *was* shot with no sign of the
   glass Sarah is scripted to hold, and raises a HIGH `missing_object` that is
   really just a missing mapping. The adapter warns about exactly this.
4. The scene and entity views the frontend renders.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.adapters import adapt_script_intelligence, adapt_vision  # noqa: E402
from app.engine import ContinuityEngine  # noqa: E402
from app.reporting.views import entity_views, project_overview, scene_views  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent
ALIASES = {"PERSON_1": "SARAH"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-aliases",
        action="store_true",
        help="Ingest the footage without the identity mapping, to show what breaks.",
    )
    args = parser.parse_args()

    script_response = json.loads(
        (EXAMPLES / "script_intelligence_response.json").read_text(encoding="utf-8")
    )
    vision_document = json.loads(
        (EXAMPLES / "vision_scene_frames.json").read_text(encoding="utf-8")
    )

    # -- 1. adapt ---------------------------------------------------------- #
    script = adapt_script_intelligence(script_response)
    footage = adapt_vision(
        vision_document, entity_aliases=None if args.no_aliases else ALIASES
    )

    print("=== ADAPTATION ===")
    print(f"script : {len(script.scene_ids)} scenes {script.scene_ids}")
    print(f"         entities: {', '.join(script.entities)}")
    print(f"         notes: {len(script.notes)} (reported to the UI, not ingested as facts)")
    print(f"footage: {footage.frames_analysed} frames -> "
          f"{len(footage.payload['observations'][0]['detections'])} aggregated observations")
    print(f"         entities: {', '.join(footage.entities)}")
    for warning in [*script.warnings, *footage.warnings]:
        print(f"         ! {warning}")

    print("\naggregated footage observations (value, confidence, source reference):")
    for detection in footage.payload["observations"][0]["detections"]:
        attribute = next(
            k for k in detection
            if k not in {"name", "type", "confidence", "timestamp", "source"}
        )
        origin = detection.get("source", "footage")
        print(f"  {detection['name']:10} {attribute:16} = {str(detection[attribute]):12} "
              f"conf {detection['confidence']:<6} {detection.get('timestamp', '')} [{origin}]")

    # -- 2. ingest --------------------------------------------------------- #
    engine = ContinuityEngine()
    script_facts = engine.ingest_script(script.payload)
    footage_facts = engine.ingest_footage(footage.payload)

    print("\n=== INGESTION ===")
    print(f"script facts : {len(script_facts)}")
    print(f"footage facts: {len(footage_facts)}")
    print(f"graph        : {engine.stats()}")
    print(f"entities     : {', '.join(sorted(engine.graph.entities()))}")

    # -- 3. analyse -------------------------------------------------------- #
    report = engine.analyse()
    print("\n=== REPORT ===")
    print(f"overall score : {report.overall_score}")
    print(f"category      : {report.category_scores}")
    print(f"summary       : {report.score_summary.main_reason}")

    if not report.issues:
        print("no issues detected")
    for issue in report.issues:
        expected_source = issue.expected.source.value if issue.expected.source else "n/a"
        observed_source = issue.observed.source.value if issue.observed.source else "n/a"
        print(f"\n[{issue.severity.value.upper()}] {issue.type} ({issue.category.value}) "
              f"in {issue.scene_id}")
        print(f"  {issue.entity.type.value} {issue.entity.name}.{issue.attribute}")
        print(f"  expected : {issue.expected.value!r} <- {expected_source} "
              f"({issue.expected.source_reference})")
        print(f"  observed : {issue.observed.value!r} <- {observed_source} "
              f"({issue.observed.source_reference})")
        print(f"  confidence {issue.confidence} · score impact -{issue.score_impact}")
        print(f"  {issue.explanation}")
        print(f"  fix: {issue.suggested_fix}")

    for assumption in report.temporary_assumptions:
        print(f"\nassumption: {assumption.description} (confidence {assumption.confidence})")

    # -- 4. dashboard views ------------------------------------------------ #
    scenes = scene_views(engine, report.issues)
    print("\n=== SCENE VIEW  (GET /continuity/scenes) ===")
    print(f"{'scene':12} {'seq':>4} {'score':>6} {'shot':>5}  location             headline")
    for scene in scenes:
        print(f"{scene.scene_id:12} {scene.sequence:>4} {scene.score:>6} "
              f"{str(scene.has_footage):>5}  {(scene.location or '—'):20} {scene.headline}")
    print(f"overview: {json.dumps(project_overview(engine, scenes))}")

    print("\n=== ENTITY VIEW  (GET /continuity/entities) ===")
    for view in entity_views(engine, report.issues):
        print(f"{view.entity.type.value} {view.entity.name} "
              f"— {view.conflict_count} conflict(s), {view.fact_count} facts")
        for slot in view.slots:
            expected = slot.expected.value if slot.expected else "—"
            observed = slot.observed.value if slot.observed else "—"
            flag = " [flagged]" if slot.flagged else ""
            print(f"    {slot.scene_id:12} {slot.attribute:20} {slot.state.value:14} "
                  f"{str(expected):18} -> {observed}{flag}")

    if args.no_aliases:
        print("\nNote: run without --no-aliases to see the same footage compared "
              "against the script.")


if __name__ == "__main__":
    main()
