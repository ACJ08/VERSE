"""Temporary assumptions derived from narrative text.

"The crowd panics and rushes through the shop" does not state that anything
moved, but it makes movement unsurprising. Assumptions encode that: they soften
penalties for a few scenes, then expire. They never override a fact, and they
never create issues of their own.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Callable, Iterable

from app.config import ProjectConfig
from app.models.schemas import Category, Fact, TemporaryAssumption

# Narrative triggers -> what they make plausible.
# Kept as data so non-Python teammates can extend the table.
_TRIGGERS: list[tuple[tuple[str, ...], str, list[Category], float]] = [
    (
        ("panic", "panics", "rush", "rushes", "stampede", "chaos", "riot"),
        "Crowd disturbance may have moved objects and disordered the environment.",
        [Category.PROPS, Category.SPATIAL, Category.MOVEMENT],
        0.6,
    ),
    (
        ("fight", "brawl", "struggle", "scuffle", "wrestle"),
        "Physical altercation may have displaced props and disturbed costume.",
        [Category.PROPS, Category.COSTUME, Category.MOVEMENT],
        0.65,
    ),
    (
        ("storm", "wind", "rain", "explosion", "earthquake", "crash"),
        "Environmental event may have altered the set and lighting.",
        [Category.PROPS, Category.LIGHTING, Category.SPATIAL],
        0.55,
    ),
    (
        ("dark", "power cut", "blackout", "lights out", "candle"),
        "Lighting conditions may have changed within the scene.",
        [Category.LIGHTING],
        0.5,
    ),
]

# Explicit state changes: these justify a specific attribute change outright.
_EXPLICIT_CHANGE_PATTERNS: list[tuple[str, str]] = [
    (r"\b(removes?|takes? off|sheds?)\b\s+(?:his|her|their|the)?\s*(.+)", "wears"),
    (r"\b(puts? on|wears?|dons?)\b\s+(?:his|her|their|the)?\s*(.+)", "wears"),
    (r"\b(drops?|puts? down|sets? down|releases?)\b\s+(?:his|her|their|the)?\s*(.+)", "holds"),
    (r"\b(picks? up|grabs?|takes?|lifts?)\b\s+(?:his|her|their|the)?\s*(.+)", "holds"),
    (r"\b(switches?|swaps?|moves?)\b\s+.*\b(hand|hands)\b", "held_in_hand"),
]


@dataclass
class ExplicitChange:
    """A scripted action that legitimises a change to one attribute."""

    entity_key: str
    attribute: str
    scene_id: str | None
    sequence: int
    source_text: str


class AssumptionEngine:
    """Extracts explicit changes and temporary assumptions from narrative facts.

    `text_extractor` is the AI hook: pass a callable to enrich extraction with
    an LLM later. Rule-based extraction always runs first.
    """

    def __init__(
        self,
        config: ProjectConfig,
        text_extractor: Callable[[str], list[str]] | None = None,
    ) -> None:
        self._config = config
        self._extractor = text_extractor
        self._assumptions: list[TemporaryAssumption] = []
        self._explicit: list[ExplicitChange] = []

    # -- extraction --------------------------------------------------------- #

    def ingest(self, facts: Iterable[Fact], sequence_of: Callable[[str | None], int]) -> None:
        """Scan narrative-bearing facts for triggers and explicit changes."""
        for fact in facts:
            text = _narrative_text(fact)
            if not text:
                continue
            sequence = sequence_of(fact.scene_id)
            self._scan_triggers(text, fact, sequence)
            self._scan_explicit(text, fact, sequence)

    def _scan_triggers(self, text: str, fact: Fact, sequence: int) -> None:
        lowered = text.lower()
        for keywords, description, categories, confidence in _TRIGGERS:
            if not any(_contains_phrase(lowered, word) for word in keywords):
                continue
            if any(a.source_text == text and a.scene_id == fact.scene_id for a in self._assumptions):
                continue
            self._assumptions.append(
                TemporaryAssumption(
                    assumption_id=f"ASSUM_{uuid.uuid4().hex[:8]}",
                    description=description,
                    scene_id=fact.scene_id,
                    created_at_sequence=sequence,
                    expires_after_scenes=self._config.assumption_ttl,
                    confidence=confidence,
                    source_text=text,
                    affects_categories=categories,
                )
            )

    def _scan_explicit(self, text: str, fact: Fact, sequence: int) -> None:
        lowered = text.lower()
        for pattern, attribute in _EXPLICIT_CHANGE_PATTERNS:
            if re.search(pattern, lowered):
                self._explicit.append(
                    ExplicitChange(
                        entity_key=fact.entity.key,
                        attribute=attribute,
                        scene_id=fact.scene_id,
                        sequence=sequence,
                        source_text=text,
                    )
                )

    # -- queries ------------------------------------------------------------ #

    def explains_change(self, entity_key: str, attribute: str, sequence: int) -> ExplicitChange | None:
        """Find a scripted action that justifies a change at or before `sequence`.

        Only the current and immediately preceding scene count — a costume
        change ten scenes ago does not excuse today's mismatch.
        """
        candidates = [
            c
            for c in self._explicit
            if c.attribute == attribute
            and c.entity_key == entity_key
            and sequence - 1 <= c.sequence <= sequence
        ]
        return max(candidates, key=lambda c: c.sequence, default=None)

    def active_for(
        self, category: Category, sequence: int, entity_key: str | None = None
    ) -> list[TemporaryAssumption]:
        return [
            a
            for a in self._assumptions
            if a.is_active_at(sequence)
            and category in a.affects_categories
            and (not a.affects_entities or entity_key in a.affects_entities)
        ]

    def mitigation(self, category: Category, sequence: int, entity_key: str | None = None) -> float:
        """Penalty multiplier in [1 - max_reduction, 1.0]. Lower = more forgiving."""
        active = self.active_for(category, sequence, entity_key)
        if not active:
            return 1.0
        strongest = max(a.confidence for a in active)
        reduction = min(strongest, self._config.max_penalty_reduction)
        return round(1.0 - reduction, 3)

    def contradict(self, assumption_id: str, reason: str) -> None:
        """Retire an assumption that later evidence disproves."""
        for assumption in self._assumptions:
            if assumption.assumption_id == assumption_id:
                assumption.active = False
                assumption.contradicted_by = reason

    @property
    def assumptions(self) -> list[TemporaryAssumption]:
        return list(self._assumptions)

    @property
    def explicit_changes(self) -> list[ExplicitChange]:
        return list(self._explicit)


# Attributes whose values are free narrative text worth scanning.
_NARRATIVE_ATTRIBUTES = {
    "action", "actions", "description", "narrative", "event", "events",
    "summary", "stage_direction", "text", "note", "notes", "synopsis",
}


def _contains_phrase(text: str, phrase: str) -> bool:
    """Whole-word match.

    Plain substring matching fires "wind" on "window" and "rain" on "brain",
    which produced assumptions that silently suppressed real issues.
    """
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def _narrative_text(fact: Fact) -> str | None:
    if not isinstance(fact.raw_value, str) or len(fact.raw_value) < 8:
        return None
    attribute = (fact.raw_attribute or fact.attribute).lower()
    if any(marker in attribute for marker in _NARRATIVE_ATTRIBUTES):
        return fact.raw_value
    return None
