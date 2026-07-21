"""Field-name and value normalisation.

Teams 1 and 2 will not agree on key names, and we do not want to force them to.
This module maps whatever arrives onto canonical attributes while keeping the
original label on the fact so the UI can show what the producer actually said.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.config import ProjectConfig
from app.models.schemas import EntityType, normalise_key

# Substrings that identify an entity type when the producer does not label one.
_TYPE_HINTS: list[tuple[EntityType, tuple[str, ...]]] = [
    (EntityType.CHARACTER, ("character", "actor", "person", "cast")),
    (EntityType.PROP, ("prop", "object", "item")),
    (EntityType.COSTUME, ("costume", "wardrobe", "outfit", "clothing")),
    (EntityType.LOCATION, ("location", "setting", "place")),
    (EntityType.LIGHTING, ("light", "lighting", "illumination")),
    (EntityType.MOVEMENT, ("movement", "motion", "blocking")),
    (EntityType.ACTION, ("action", "event", "beat")),
    (EntityType.SCENE, ("scene",)),
]


class Normaliser:
    """Canonicalises attribute names and values using the project config."""

    def __init__(self, config: ProjectConfig) -> None:
        self._config = config
        self._attribute_lookup = self._build_lookup(config.attribute_aliases)
        self._value_lookup = self._build_lookup(config.value_synonyms)

    @staticmethod
    def _build_lookup(aliases: dict[str, list[str]]) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for canonical, variants in aliases.items():
            lookup[normalise_key(canonical)] = canonical
            for variant in variants:
                lookup[normalise_key(variant)] = canonical
        return lookup

    # -- attributes --------------------------------------------------------- #

    def attribute(self, raw: str) -> str:
        """Map a producer's field name onto a canonical attribute name."""
        key = normalise_key(raw)
        if key in self._attribute_lookup:
            return self._attribute_lookup[key]
        # Fall back to fuzzy matching so a typo or a novel phrasing still lands.
        match = self._closest(key, self._attribute_lookup)
        return match or key

    # -- values ------------------------------------------------------------- #

    def value(self, raw: object) -> object:
        """Collapse synonymous values ("navy jacket" -> "blue_jacket").

        Non-string values pass through untouched — numbers and booleans are
        already canonical.
        """
        if not isinstance(raw, str):
            return raw
        key = normalise_key(raw)
        if key in self._value_lookup:
            return self._value_lookup[key]
        match = self._closest(key, self._value_lookup)
        return match or key

    def values_match(self, left: object, right: object) -> bool:
        """True when two values mean the same thing after normalisation."""
        a, b = self.value(left), self.value(right)
        if a == b:
            return True
        if isinstance(a, str) and isinstance(b, str):
            threshold = self._config.threshold("value_match_similarity", 0.85)
            return _similarity(a, b) >= threshold
        return False

    # -- entity types ------------------------------------------------------- #

    @staticmethod
    def entity_type(hint: str) -> EntityType:
        """Best-effort type inference from a container key or explicit label."""
        lowered = str(hint).lower()
        for entity_type, needles in _TYPE_HINTS:
            if any(needle in lowered for needle in needles):
                return entity_type
        return EntityType.CUSTOM

    # -- internals ---------------------------------------------------------- #

    def _closest(self, key: str, lookup: dict[str, str]) -> str | None:
        threshold = self._config.threshold("entity_match_similarity", 0.72)
        best, best_score = None, 0.0
        for candidate, canonical in lookup.items():
            score = _similarity(key, candidate)
            if score > best_score:
                best, best_score = canonical, score
        return best if best_score >= threshold else None


def _similarity(a: str, b: str) -> float:
    """Token-aware string similarity in [0, 1].

    Pure ratio under-scores "blue blazer" vs "navy jacket"; shared tokens matter
    more than character overlap for wardrobe and prop descriptions.
    """
    if a == b:
        return 1.0
    ratio = SequenceMatcher(None, a, b).ratio()
    tokens_a = set(re.split(r"[_\s]+", a)) - {""}
    tokens_b = set(re.split(r"[_\s]+", b)) - {""}
    if tokens_a and tokens_b:
        overlap = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
        return max(ratio, overlap)
    return ratio
