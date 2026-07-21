"""Entity identity resolution.

"Sarah", "SARAH", and "Sarah Chen" should all resolve to the same character
node. Rules first (exact key, containment), AI second — the AI hook is left as
a pluggable callable so we can swap in watsonx/Granite without touching the
graph code.
"""

from __future__ import annotations

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
        threshold = self._config.threshold("entity_match_similarity", 0.72)
        best: EntityRef | None = None
        best_score = 0.0

        for candidate in self._canonical.values():
            if not _types_compatible(candidate.type, entity.type):
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


def _types_compatible(a: EntityType, b: EntityType) -> bool:
    """CUSTOM matches anything; otherwise types must agree."""
    return a is b or EntityType.CUSTOM in (a, b)


def keyword_semantic_matcher(
    synonyms: dict[str, list[str]],
) -> Callable[[str, str], float]:
    """Cheap stand-in for an LLM matcher, driven by the config synonym table.

    Swap this for a watsonx/Granite embedding call when team 1's model is up;
    the signature is all `EntityMatcher` depends on.
    """
    groups: list[set[str]] = []
    for canonical, variants in synonyms.items():
        groups.append({canonical.lower(), *(v.lower() for v in variants)})

    def match(left: str, right: str) -> float:
        l, r = left.lower(), right.lower()
        for group in groups:
            if any(term in l for term in group) and any(term in r for term in group):
                return 0.9
        return 0.0

    return match
