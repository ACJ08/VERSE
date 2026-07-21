"""Human-in-the-loop handling.

Humans are the final authority. This module applies their decisions to the
issue list, records fact overrides at the highest trust level, and preserves
everything in history — a dismissed issue is suppressed, never deleted.
"""

from __future__ import annotations

import uuid
from collections import defaultdict

from app.config import ProjectConfig
from app.graph.builder import KnowledgeGraph
from app.models.schemas import (
    EntityRef,
    Fact,
    FactEdit,
    FactOverride,
    FeedbackAction,
    Issue,
    IssueStatus,
    SourceRef,
    SourceType,
)

_ACTION_STATUS = {
    "confirm": IssueStatus.CONFIRMED,
    "dismiss": IssueStatus.DISMISSED,
    "resolve": IssueStatus.RESOLVED,
    "reopen": IssueStatus.PENDING_REVIEW,
}


class FeedbackManager:
    """Applies feedback and exposes the learning signal it produces."""

    def __init__(self, graph: KnowledgeGraph, config: ProjectConfig) -> None:
        self._graph = graph
        self._config = config
        self._actions: list[FeedbackAction] = []
        # (entity_key, attribute, rule_id) -> dismissal count
        self._dismissed: dict[tuple[str, str, str], int] = defaultdict(int)

    # -- issue decisions ---------------------------------------------------- #

    def apply(self, action: FeedbackAction, issues: list[Issue]) -> Issue | None:
        """Apply one decision. Returns the affected issue, or None if unknown."""
        target = next((i for i in issues if i.issue_id == action.issue_id), None)
        if target is None:
            return None

        target.status = _ACTION_STATUS[action.action]
        self._actions.append(action)

        signature = (target.entity.key, target.attribute, target.type)
        if action.action == "dismiss":
            self._dismissed[signature] += 1
        elif action.action == "reopen":
            self._dismissed.pop(signature, None)
        return target

    def apply_many(self, actions: list[FeedbackAction], issues: list[Issue]) -> list[Issue]:
        return [i for i in (self.apply(a, issues) for a in actions) if i is not None]

    # -- fact overrides ----------------------------------------------------- #

    def override_fact(self, override: FactOverride) -> Fact:
        """Record a human-authored fact. Outranks every AI-produced fact.

        The previous value is kept in `history` rather than being overwritten.
        """
        existing = self._graph.facts_for(
            override.entity_key, override.attribute, override.scene_id
        )
        entity = self._graph.entity(override.entity_key) or EntityRef(name=override.entity_key)

        human = next((f for f in existing if f.human_confirmed), None)
        if human is not None:
            edited = human.model_copy(
                update={
                    "value": override.value,
                    "raw_value": override.value,
                    "history": [
                        *human.history,
                        FactEdit(
                            actor=override.actor,
                            previous_value=human.value,
                            reason=override.reason,
                        ),
                    ],
                }
            )
            self._graph.replace_fact(edited)
            return edited

        fact = Fact(
            fact_id=f"FACT_{uuid.uuid4().hex[:10]}",
            entity=entity,
            attribute=override.attribute,
            value=override.value,
            raw_value=override.value,
            scene_id=override.scene_id,
            sequence=self._graph.timeline.sequence_of(override.scene_id),
            source=SourceRef(type=SourceType.HUMAN, reference=f"{override.actor} override"),
            confidence=1.0,
            trust=self._config.trust(SourceType.HUMAN),
            human_confirmed=True,
            history=[FactEdit(actor=override.actor, reason=override.reason)],
        )
        self._graph.add_facts([fact])
        return fact

    # -- learning signal ---------------------------------------------------- #

    def dismissed_patterns(self) -> list[tuple[str, str, str]]:
        """Patterns the user has accepted as intentional, for suppression."""
        return list(self._dismissed.keys())

    def adjustment_for(self, entity_key: str, attribute: str, rule_id: str) -> float:
        """Small confidence discount for repeatedly dismissed patterns.

        Deliberately weak: user decisions inform the engine, they do not retrain it.
        """
        count = self._dismissed.get((entity_key, attribute, rule_id), 0)
        return max(0.5, 1.0 - 0.1 * count)

    @property
    def history(self) -> list[FeedbackAction]:
        return list(self._actions)
