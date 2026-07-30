"""Derived read models for the dashboard.

`ContinuityReport` answers "what is wrong?". The dashboard also asks two
questions the report does not cover:

* **Per scene** — what is this scene, was it shot, what did it score, what went
  wrong in it? (scene tracking, scene timeline, narrative progression screens)
* **Per entity** — what does the production believe about Sarah's jacket right
  now, where did that belief come from, and has footage confirmed it?
  (costume tracking, prop tracking, production memory screens)

Both are computed from the graph and the memory that already exist — nothing new
is stored, and scoring goes through the same `CategoryScorer` the report uses so
a scene's score cannot drift from the project's.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.models.schemas import (
    AttributeState,
    EntityRef,
    EntityType,
    EntityView,
    Fact,
    Issue,
    ObservationRef,
    SceneView,
    Severity,
    SlotView,
    SourceType,
)
from app.scoring.overall_score import overall_score

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.engine import ContinuityEngine

# Slots that describe the payload or the scene envelope rather than a tracked
# state of a production element.
_NON_TRACKED_ATTRIBUTES = {"slugline", "int_ext", "action", "shoot_date", "call_time"}


# --------------------------------------------------------------------------- #
# Scenes
# --------------------------------------------------------------------------- #


def scene_views(engine: ContinuityEngine, issues: list[Issue] | None = None) -> list[SceneView]:
    """One `SceneView` per scene the engine knows about, in screenplay order.

    `issues` defaults to the issues from the last `analyse()` call, so callers
    that already have a report do not pay for a second detection pass.
    """
    issue_list = engine.issues() if issues is None else issues
    by_scene: dict[str, list[Issue]] = {}
    for issue in issue_list:
        by_scene.setdefault(issue.scene_id or "", []).append(issue)

    views: list[SceneView] = []
    for node in engine.graph.timeline.ordered():
        facts = engine.graph.facts_in_scene(node.scene_id)
        scene_issues = by_scene.get(node.scene_id, [])
        category_scores, _, _ = engine.scorer.score(
            scene_issues, engine.graph.timeline.sequence_of
        )
        sources = _sources(facts)

        views.append(
            SceneView(
                scene_id=node.scene_id,
                sequence=node.sequence,
                location=_scene_attribute(facts, "location"),
                time_of_day=_scene_attribute(facts, "time_of_day"),
                slugline=_scene_attribute(facts, "slugline"),
                score=overall_score(engine.config, category_scores),
                category_scores=category_scores,
                issue_count=len(scene_issues),
                issues_by_severity=_count_by_severity(scene_issues),
                categories=sorted({i.category for i in scene_issues}, key=lambda c: c.value),
                entities=_scene_entities(engine, facts),
                sources=sources,
                has_footage=SourceType.FOOTAGE in sources,
                fact_count=len(facts),
                headline=_headline(scene_issues, SourceType.FOOTAGE in sources),
            )
        )
    return views


def _scene_attribute(facts: list[Fact], attribute: str) -> str | None:
    """Most trusted raw value of a scene-level attribute, for display.

    Restricted to facts about the scene itself: props carry a `location`
    attribute too ("glass on the table"), which would otherwise be reported as
    the scene's location.

    The raw value is preferred over the normalised one so the UI shows
    "INT. COFFEE SHOP - DAY" rather than "int_coffee_shop_day".
    """
    candidates = [
        f for f in facts if f.attribute == attribute and f.entity.type is EntityType.SCENE
    ]
    if not candidates:
        return None
    best = max(candidates, key=lambda f: f.weight)
    value = best.raw_value if best.raw_value is not None else best.value
    return str(value)


def _scene_entities(engine: ContinuityEngine, facts: list[Fact]) -> list[EntityRef]:
    seen: dict[str, EntityRef] = {}
    for fact in facts:
        if fact.entity.type is EntityType.SCENE:
            continue
        seen.setdefault(fact.entity.key, fact.entity)
    return [seen[key] for key in sorted(seen)]


def _sources(facts: list[Fact]) -> list[SourceType]:
    return sorted({f.source.type for f in facts}, key=lambda s: s.value)


def _count_by_severity(issues: list[Issue]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for issue in issues:
        counts[issue.severity.value] = counts.get(issue.severity.value, 0) + 1
    return counts


def _headline(issues: list[Issue], has_footage: bool) -> str:
    """One line a producer can read without opening the scene."""
    if not issues:
        return "No continuity issues detected." if has_footage else "Not shot yet — script only."
    worst = max(issues, key=lambda i: _SEVERITY_ORDER.index(i.severity))
    others = len(issues) - 1
    tail = f" (+{others} more)" if others else ""
    return f"{worst.severity.value.title()}: {worst.type.replace('_', ' ')}{tail}"


_SEVERITY_ORDER = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]


# --------------------------------------------------------------------------- #
# Entities
# --------------------------------------------------------------------------- #


def entity_views(
    engine: ContinuityEngine,
    issues: list[Issue] | None = None,
    *,
    entity_types: set[str] | None = None,
    attributes: set[str] | None = None,
) -> list[EntityView]:
    """One `EntityView` per production element, with its per-scene slots.

    `entity_types` filters to e.g. {"character"} or {"prop"}; `attributes`
    filters to e.g. {"wears"} for a costume screen.
    """
    issue_index = _issue_index(engine.issues() if issues is None else issues)
    views: dict[str, EntityView] = {}

    for scene in engine.graph.timeline.ordered():
        for slot in engine.memory.iter_slots(scene.scene_id):
            entity = engine.graph.entity(slot.entity_key)
            if entity is None or entity.type is EntityType.SCENE:
                continue
            if entity_types is not None and entity.type.value not in entity_types:
                continue
            if slot.attribute in _NON_TRACKED_ATTRIBUTES:
                continue
            if attributes is not None and slot.attribute not in attributes:
                continue

            issue = issue_index.get((slot.entity_key, slot.attribute, scene.scene_id))
            view = views.setdefault(
                slot.entity_key, EntityView(entity=entity)
            )
            slot_view = SlotView(
                entity=entity,
                attribute=slot.attribute,
                scene_id=scene.scene_id,
                state=_state(engine, slot, issue),
                expected=_observation(slot.expected),
                observed=_observation(slot.observed),
                issue_id=issue.issue_id if issue else None,
                severity=issue.severity if issue else None,
                human_confirmed=any(f.human_confirmed for f in slot.history),
                flagged=issue is not None,
            )
            view.slots.append(slot_view)
            if scene.scene_id not in view.scene_ids:
                view.scene_ids.append(scene.scene_id)
            if slot.attribute not in view.attributes:
                view.attributes.append(slot.attribute)
            if slot_view.state is AttributeState.CONFLICT:
                view.conflict_count += 1
            if issue is not None:
                view.issue_count += 1

            current = slot.expected or slot.observed
            if current is not None:
                view.latest[slot.attribute] = (
                    current.raw_value if current.raw_value is not None else current.value
                )

    for key, view in views.items():
        view.fact_count = len(engine.graph.facts_for_entity(key))
        view.attributes.sort()

    return [views[key] for key in sorted(views)]


def _issue_index(issues: list[Issue]) -> dict[tuple[str, str, str | None], Issue]:
    return {(i.entity.key, i.attribute, i.scene_id): i for i in issues}


def _state(engine: ContinuityEngine, slot: Any, issue: Issue | None) -> AttributeState:
    if issue is not None:
        return AttributeState.CONFLICT
    if slot.expected is not None and slot.observed is not None:
        matched = engine.normaliser.values_match(slot.expected.value, slot.observed.value)
        return AttributeState.MATCH if matched else AttributeState.CONFLICT
    if slot.expected is not None:
        return AttributeState.UNVERIFIED
    return AttributeState.OBSERVED_ONLY


def _observation(fact: Fact | None) -> ObservationRef | None:
    if fact is None:
        return None
    return ObservationRef(
        value=fact.raw_value if fact.raw_value is not None else fact.value,
        source=fact.source.type,
        source_reference=fact.source.reference,
        confidence=fact.confidence,
    )


# --------------------------------------------------------------------------- #
# Project rollup
# --------------------------------------------------------------------------- #


def project_overview(engine: ContinuityEngine, scenes: list[SceneView]) -> dict[str, Any]:
    """Counters the dashboard header cards need, derived from the scene views."""
    shot = [s for s in scenes if s.has_footage]
    scored = [s.score for s in shot] or [s.score for s in scenes]
    return {
        "scenes_total": len(scenes),
        "scenes_shot": len(shot),
        "scenes_clean": len([s for s in shot if s.issue_count == 0]),
        "issues_total": sum(s.issue_count for s in scenes),
        "average_scene_score": round(sum(scored) / len(scored), 1) if scored else 100.0,
        "facts": engine.stats().get("facts", 0),
        "entities": engine.stats().get("entities", 0),
        "categories_at_risk": sorted(
            {c.value for s in scenes for c in s.categories}
        ),
    }


__all__ = ["entity_views", "project_overview", "scene_views"]
