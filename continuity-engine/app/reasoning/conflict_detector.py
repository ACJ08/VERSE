"""Conflict detection.

Walks every (entity, attribute) slot in a scene, runs the applicable rules, and
converts surviving verdicts into Issues. Suppression happens here rather than
inside rules so that every rule benefits from it:

  * explicit scripted changes cancel the issue outright
  * temporary assumptions reduce severity and score impact
  * dismissed issues stay suppressed on re-runs
  * repeats across scenes escalate severity
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from app.config import ProjectConfig
from app.graph.builder import KnowledgeGraph
from app.graph.memory import OBSERVATION_SOURCES, ProductionMemory
from app.ingestion.normaliser import Normaliser
from app.models.schemas import EntityRef, Issue, ObservationRef, Severity
from app.reasoning.assumptions import AssumptionEngine
from app.reasoning.rules import REGISTRY, RuleContext, RuleRegistry

_SEVERITY_ORDER = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]


class ConflictDetector:
    """Produces Issues for one scene or a whole project."""

    def __init__(
        self,
        graph: KnowledgeGraph,
        memory: ProductionMemory,
        config: ProjectConfig,
        assumptions: AssumptionEngine,
        normaliser: Normaliser,
        registry: RuleRegistry | None = None,
    ) -> None:
        self._graph = graph
        self._memory = memory
        self._config = config
        self._assumptions = assumptions
        self._normaliser = normaliser
        self._registry = registry or REGISTRY
        self._dismissed: set[tuple[str, str, str]] = set()  # (entity, attribute, rule)
        self._seen: dict[tuple[str, str, str], list[str]] = defaultdict(list)

    # -- dismissal memory --------------------------------------------------- #

    def dismiss_pattern(self, entity_key: str, attribute: str, rule_id: str) -> None:
        """Stop penalising an accepted condition on future runs."""
        self._dismissed.add((entity_key, attribute, rule_id))

    def is_dismissed(self, entity_key: str, attribute: str, rule_id: str) -> bool:
        return (entity_key, attribute, rule_id) in self._dismissed

    # -- detection ---------------------------------------------------------- #

    def detect_scene(self, scene_id: str) -> list[Issue]:
        issues: list[Issue] = []
        has_footage = self._scene_has_footage(scene_id)
        sequence = self._graph.timeline.sequence_of(scene_id)

        for slot in self._memory.iter_slots(scene_id):
            for registered in self._registry.for_attribute(slot.attribute):
                signature = (slot.entity_key, slot.attribute, registered.id)
                if self.is_dismissed(*signature):
                    continue

                context = RuleContext(
                    slot=slot,
                    config=self._config,
                    normaliser=self._normaliser,
                    scene_id=scene_id,
                    proximity=self._expectation_proximity(slot, scene_id),
                    prior_occurrences=len(self._seen[signature]),
                    scene_has_footage=has_footage,
                )

                result = registered.fn(context)
                if result is None:
                    continue
                if result.confidence < self._config.threshold("min_conflict_confidence", 0.4):
                    continue

                explicit = self._assumptions.explains_change(
                    slot.entity_key, slot.attribute, sequence
                )
                if explicit is not None:
                    continue  # the script itself accounts for this change

                issues.append(self._build_issue(result, slot, scene_id, sequence, signature))

        return issues

    def detect_all(self) -> list[Issue]:
        issues: list[Issue] = []
        for scene_id in self._graph.scene_ids():
            issues.extend(self.detect_scene(scene_id))
        return issues

    # -- issue construction ------------------------------------------------- #

    def _build_issue(self, result, slot, scene_id, sequence, signature) -> Issue:
        expected, observed = slot.expected, slot.observed
        mitigations = self._assumptions.active_for(result.category, sequence, slot.entity_key)
        occurrences = len(self._seen[signature]) + 1
        self._seen[signature].append(scene_id)

        severity = self._adjust_severity(result.severity, occurrences)
        anchor = expected or observed  # at least one exists or no rule would have fired
        entity = self._graph.entity(slot.entity_key) or (
            anchor.entity if anchor else EntityRef(name=slot.entity_key)
        )

        return Issue(
            issue_id=f"ISSUE_{uuid.uuid4().hex[:8].upper()}",
            category=result.category,
            type=result.rule_id,
            severity=severity,
            confidence=result.confidence,
            entity=entity,
            attribute=slot.attribute,
            scene_id=scene_id,
            expected=_observation(expected),
            observed=_observation(observed),
            explanation=result.explanation,
            suggested_fix=result.suggested_fix,
            occurrences=occurrences,
            related_scene_ids=list(self._seen[signature]),
            mitigated_by=[a.assumption_id for a in mitigations],
            supporting_fact_ids=[f.fact_id for f in (expected, observed) if f is not None],
        )

    def _adjust_severity(self, base: Severity, occurrences: int) -> Severity:
        """Severity reflects the intrinsic seriousness of the error, plus repetition.

        Narrative mitigation deliberately does *not* lower severity — it is
        applied once, as a penalty multiplier in scoring. Doing both meant a
        justified issue was discounted twice and effectively disappeared.
        """
        index = _SEVERITY_ORDER.index(base)
        if occurrences >= self._config.escalate_after:
            index = min(index + 1, len(_SEVERITY_ORDER) - 1)
        return _SEVERITY_ORDER[index]

    # -- helpers ------------------------------------------------------------ #

    def _scene_has_footage(self, scene_id: str) -> bool:
        return any(
            f.scene_id == scene_id and f.source.type in OBSERVATION_SOURCES
            for f in self._graph.all_facts()
        )

    def _expectation_proximity(self, slot, scene_id: str) -> float:
        """How close the governing expectation is in screenplay order."""
        if slot.expected is None:
            return 1.0
        return self._graph.timeline.proximity(scene_id, slot.expected.scene_id)


def _observation(fact) -> ObservationRef:
    if fact is None:
        return ObservationRef()  # absence: nothing observed, no source to cite
    return ObservationRef(
        value=fact.raw_value if fact.raw_value is not None else fact.value,
        source=fact.source.type,
        source_reference=fact.source.reference,
        confidence=fact.confidence,
    )
