"""Entity identity resolution.

"Sarah", "SARAH", and "Sarah Chen" should all resolve to the same character
node. Rules first (exact key, containment), AI second — the AI hook is left as
a pluggable callable so we can swap in watsonx/Granite without touching the
graph code.
"""

from __future__ import annotations

import re
from typing import Callable, Protocol

from app.config import ProjectConfig
from app.ingestion.normaliser import _similarity
from app.models.schemas import EntityRef, EntityType


class SemanticMatcher(Protocol):
    """Optional AI fallback. Returns similarity in [0, 1]."""

    def __call__(self, left: str, right: str) -> float: ...


class EntityMatcher:
    """Maintains a registry of canonical entities and resolves aliases to them.

    Matching is scoped by entity type so a prop named "Sarah" never merges into
    a character named "Sarah".
    """

    def __init__(
        self,
        config: ProjectConfig,
        semantic_matcher: SemanticMatcher | None = None,
    ) -> None:
        self._config = config
        self._semantic = semantic_matcher
        self._canonical: dict[str, EntityRef] = {}
        self._aliases: dict[str, str] = {}  # alias key -> canonical key

    @property
    def entities(self) -> dict[str, EntityRef]:
        return dict(self._canonical)

    def resolve(self, entity: EntityRef) -> EntityRef:
        """Return the canonical EntityRef for `entity`, registering it if new."""
        existing = self._canonical.get(entity.key)
        if existing is not None and _types_compatible(existing.type, entity.type):
            return existing
        if existing is None and entity.key in self._aliases:
            return self._canonical[self._aliases[entity.key]]

        match = self._find_match(entity)
        if match is not None:
            self._aliases[entity.key] = match.key
            return match

        # Keys stay human-readable ("sarah"), so a same-name entity of another
        # type gets a type suffix rather than silently merging.
        registered = entity
        if existing is not None:
            registered = entity.model_copy(update={"key": f"{entity.key}_{entity.type.value}"})
        self._canonical[registered.key] = registered
        return registered

    def _find_match(self, entity: EntityRef) -> EntityRef | None:
        # Scene ids are exact identifiers, never fuzzy names: "SCENE_011" and
        # "SCENE_012" score 0.89 on string similarity but are different scenes.
        if entity.type is EntityType.SCENE:
            return None

        threshold = self._config.threshold("entity_match_similarity", 0.72)
        best: EntityRef | None = None
        best_score = 0.0

        for candidate in self._canonical.values():
            if not _types_compatible(candidate.type, entity.type):
                continue
            if _enumerated_siblings(entity.key, candidate.key):
                continue
            score = _similarity(entity.key, candidate.key)
            if score < threshold and self._semantic is not None:
                score = max(score, self._semantic(entity.name, candidate.name))
            if score > best_score:
                best, best_score = candidate, score

        return best if best_score >= threshold else None

    def alias_map(self) -> dict[str, str]:
        """Exposed for reporting so the UI can explain why two names merged."""
        return dict(self._aliases)


_ENUMERATED = re.compile(r"^(?P<stem>.*?)[_\-]?(?P<number>\d+)$")


def _enumerated_siblings(a: str, b: str) -> bool:
    """True for two members of the same numbered series ("person_2" / "person_3").

    Vision tracks people as PERSON_1, PERSON_2, ... — names that differ by one
    digit and so score 0.88 on string similarity. They are distinct tracks, and
    merging them attributes one person's wardrobe to another.
    """
    left, right = _ENUMERATED.match(a), _ENUMERATED.match(b)
    if left is None or right is None:
        return False
    return (
        left.group("stem") == right.group("stem")
        and left.group("number") != right.group("number")
    )


def _types_compatible(a: EntityType, b: EntityType) -> bool:
    """CUSTOM matches anything; otherwise types must agree."""
    return a is b or EntityType.CUSTOM in (a, b)


def keyword_semantic_matcher(
    synonyms: dict[str, list[str]],
) -> Callable[[str, str], float]:
    """Cheap stand-in for an LLM matcher, driven by the config synonym table.

    Swap this for a watsonx/Granite embedding call when team 1's model is up;
    the signature is all `EntityMatcher` depends on.

    Matching is whole-word only. Substring matching merged the characters
    "Sarah" and "Marcus", because the one-letter synonym "r" (for "right hand")
    appears inside both names.
    """
    groups: list[set[str]] = []
    for canonical, variants in synonyms.items():
        groups.append({canonical.lower(), *(v.lower() for v in variants)})

    def match(left: str, right: str) -> float:
        l, r = left.lower(), right.lower()
        for group in groups:
            if any(_mentions(l, term) for term in group) and any(_mentions(r, term) for term in group):
                return 0.9
        return 0.0

    return match


def _mentions(text: str, term: str) -> bool:
    """Whole-word containment.

    Naive substring matching let the one-letter hand shorthands ("l", "r") in
    the value synonym table match almost any pair of names — "SARAH" and
    "PERSON_2" both contain an "r" — merging unrelated entities. Short terms now
    have to match the whole value; longer ones must land on a word boundary so
    "glass" still matches "wine glass" without "ass" matching anything.
    """
    if len(term) < 3:
        return text == term
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None
