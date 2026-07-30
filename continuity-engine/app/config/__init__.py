"""Project configuration loading.

All tunable behaviour (trust, weights, thresholds, aliases) lives in
``project_config.json`` so a production can be re-tuned without code changes.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models.schemas import Category, Severity, SourceType

_DEFAULT_PATH = Path(__file__).with_name("project_config.json")


class ProjectConfig:
    """Typed accessors over the raw config dict.

    Deliberately thin: callers read through methods so we can change the file
    layout later without touching the reasoning code.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    # -- loading ------------------------------------------------------------ #

    @classmethod
    def load(cls, path: str | Path | None = None) -> "ProjectConfig":
        target = Path(path) if path else _DEFAULT_PATH
        with target.open(encoding="utf-8") as fh:
            return cls(json.load(fh))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectConfig":
        """Merge a partial override over the defaults — used by tests and API callers."""
        base = json.loads(_DEFAULT_PATH.read_text(encoding="utf-8"))
        return cls(_deep_merge(base, data))

    # -- accessors ---------------------------------------------------------- #

    @property
    def project_id(self) -> str:
        return self._data.get("project_id", "VERSE")

    @property
    def engine_version(self) -> str:
        return self._data.get("engine_version", "0.1.0")

    def trust(self, source: SourceType) -> float:
        return float(self._data.get("trust_levels", {}).get(source.value, 0.3))

    def category_weight(self, category: Category | str) -> float:
        key = category.value if isinstance(category, Category) else str(category)
        return float(self._data.get("category_weights", {}).get(key, 1.0))

    def severity_penalty(self, severity: Severity) -> float:
        return float(self._data.get("severity_penalties", {}).get(severity.value, 10))

    def threshold(self, name: str, default: float = 0.0) -> float:
        return float(self._data.get("thresholds", {}).get(name, default))

    @property
    def attribute_aliases(self) -> dict[str, list[str]]:
        return _alias_table(self._data.get("attribute_aliases", {}))

    @property
    def value_synonyms(self) -> dict[str, list[str]]:
        return _alias_table(self._data.get("value_synonyms", {}))

    @property
    def entity_aliases(self) -> dict[str, list[str]]:
        """Producer-specific entity name aliases ("PERSON_1" -> "Sarah").

        Vision tracks anonymous ids and the script names people; this table is
        how a production declares the join. Consumed by the vision adapter.
        """
        return _alias_table(self._data.get("entity_aliases", {}))

    @property
    def assumption_ttl(self) -> int:
        return int(self._data.get("assumptions", {}).get("default_expires_after_scenes", 2))

    @property
    def max_penalty_reduction(self) -> float:
        return float(self._data.get("assumptions", {}).get("max_penalty_reduction", 0.7))

    @property
    def escalate_after(self) -> int:
        return int(self._data.get("repetition", {}).get("escalate_after_occurrences", 2))

    @property
    def categories(self) -> list[str]:
        known = [c.value for c in Category]
        return known + [c for c in self._data.get("custom_categories", []) if c not in known]

    def raw(self) -> dict[str, Any]:
        return self._data


def _alias_table(raw: dict[str, Any]) -> dict[str, list[str]]:
    """Keep only real alias groups from a config table.

    The config files carry `_note` documentation strings alongside the data.
    Without this filter a note is iterated character by character, so every
    single letter becomes an alias — which made the keyword semantic matcher
    score any two names at 0.9 and merge unrelated entities into one node.
    """
    return {
        canonical: [str(v) for v in variants]
        for canonical, variants in raw.items()
        if not canonical.startswith("_") and isinstance(variants, list)
    }


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


@lru_cache(maxsize=1)
def default_config() -> ProjectConfig:
    return ProjectConfig.load()


__all__ = ["ProjectConfig", "default_config"]
