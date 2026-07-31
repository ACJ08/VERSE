"""Project configuration loading.

All tunable behaviour (trust weights, severity penalties, thresholds, and alias
tables) lives in ``project_config.json`` so a production team can fine-tune the
engine without modifying Python code. The file is loaded once and cached.

Typical usage
-------------
    from app.config import ProjectConfig, default_config

    # Read the shared default config (cached after first call)
    cfg = default_config()

    # Per-project override — merges on top of the defaults so only the
    # fields that differ need to be specified (used by the API on every request)
    cfg = ProjectConfig.from_dict({"project_id": "abc-123", "thresholds": {"min_confidence": 0.7}})
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models.schemas import Category, Severity, SourceType

# Path to the default config file that ships with the package
_DEFAULT_PATH = Path(__file__).with_name("project_config.json")


class ProjectConfig:
    """Typed accessors over the raw config dict.

    Deliberately thin: callers read through methods so we can change the file
    layout later without touching the reasoning code.  No business logic here —
    just parsing and defaulting.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    # ── loading ──────────────────────────────────────────────────────────────

    @classmethod
    def load(cls, path: str | Path | None = None) -> "ProjectConfig":
        """Load config from *path*, defaulting to the bundled project_config.json."""
        target = Path(path) if path else _DEFAULT_PATH
        with target.open(encoding="utf-8") as fh:
            return cls(json.load(fh))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectConfig":
        """Merge a partial override dict on top of the defaults.

        Used by the API layer (projects router, routes router) so every
        request gets a per-project config with minimal boilerplate:
            config = ProjectConfig.from_dict({"project_id": project_id})
        """
        base = json.loads(_DEFAULT_PATH.read_text(encoding="utf-8"))
        return cls(_deep_merge(base, data))

    # ── accessors ────────────────────────────────────────────────────────────

    @property
    def project_id(self) -> str:
        """Unique project identifier used as the primary key in FactStore."""
        return self._data.get("project_id", "VERSE")

    @property
    def engine_version(self) -> str:
        """Semantic version string included in every ContinuityReport."""
        return self._data.get("engine_version", "0.1.0")

    def trust(self, source: SourceType) -> float:
        """Confidence multiplier for facts produced by *source*.

        A screenplay fact (trust ~0.9) is treated as more authoritative than
        a vision detection (trust ~0.6) because the script is the production's
        ground truth. Override in project_config.json per production.
        """
        return float(self._data.get("trust_levels", {}).get(source.value, 0.3))

    def category_weight(self, category: Category | str) -> float:
        """Weight applied to *category*'s score in the overall continuity score."""
        key = category.value if isinstance(category, Category) else str(category)
        return float(self._data.get("category_weights", {}).get(key, 1.0))

    def severity_penalty(self, severity: Severity) -> float:
        """Score penalty (0-100 scale) applied for each issue at *severity* level."""
        return float(self._data.get("severity_penalties", {}).get(severity.value, 10))

    def threshold(self, name: str, default: float = 0.0) -> float:
        """Look up a named threshold, e.g. 'min_confidence' or 'fuzzy_match_ratio'."""
        return float(self._data.get("thresholds", {}).get(name, default))

    @property
    def attribute_aliases(self) -> dict[str, list[str]]:
        """Synonymous attribute names — e.g. 'wears' == 'costume' == 'outfit'.

        Allows the engine to match facts produced by different extractors that
        use different vocabulary for the same physical attribute.
        """
        return _alias_table(self._data.get("attribute_aliases", {}))

    @property
    def value_synonyms(self) -> dict[str, list[str]]:
        """Synonymous attribute values — e.g. 'navy' == 'dark blue' == 'navy blue'.

        Used by the keyword semantic matcher so lexically different strings that
        mean the same thing are not flagged as continuity conflicts.
        """
        return _alias_table(self._data.get("value_synonyms", {}))

    @property
    def entity_aliases(self) -> dict[str, list[str]]:
        """Producer-supplied entity name aliases — e.g. 'PERSON_1' → 'Sarah'.

        Vision tracking assigns anonymous IDs to detected people; the script
        uses character names. This table is how a production declares the join
        between the two worlds. Consumed by the vision adapter at ingest time.
        """
        return _alias_table(self._data.get("entity_aliases", {}))

    @property
    def assumption_ttl(self) -> int:
        """Number of scenes an assumption stays valid before it is retired."""
        return int(self._data.get("assumptions", {}).get("default_expires_after_scenes", 2))

    @property
    def max_penalty_reduction(self) -> float:
        """Maximum fraction (0-1) by which active assumptions can reduce a penalty."""
        return float(self._data.get("assumptions", {}).get("max_penalty_reduction", 0.7))

    @property
    def escalate_after(self) -> int:
        """Number of recurrences before an issue severity is escalated."""
        return int(self._data.get("repetition", {}).get("escalate_after_occurrences", 2))

    @property
    def categories(self) -> list[str]:
        """All category names: built-in enum values plus any custom ones in the config."""
        known = [c.value for c in Category]
        return known + [c for c in self._data.get("custom_categories", []) if c not in known]

    def raw(self) -> dict[str, Any]:
        """Return the raw config dict — use sparingly; prefer typed accessors."""
        return self._data


# ── Helpers ───────────────────────────────────────────────────────────────────

def _alias_table(raw: dict[str, Any]) -> dict[str, list[str]]:
    """Filter a raw config section down to real alias groups only.

    project_config.json uses "_note" keys as inline documentation strings:
        "value_synonyms": {
            "_note": "Add synonyms for attribute values here.",
            "navy": ["dark blue", "navy blue"]
        }
    Without this filter the note string is iterated character by character
    inside the keyword semantic matcher, so every single letter becomes an
    alias — which made the matcher score any two names at ~0.9 and merge
    completely unrelated entities into one knowledge graph node.
    """
    return {
        canonical: [str(v) for v in variants]
        for canonical, variants in raw.items()
        # Skip documentation keys (start with underscore) and non-list values
        if not canonical.startswith("_") and isinstance(variants, list)
    }


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *override* into *base*, modifying base in place.

    Nested dicts are merged; all other types (lists, scalars) are replaced.
    This means from_dict({"thresholds": {"min_confidence": 0.7}}) only changes
    that one threshold and keeps all other thresholds from the default config.
    """
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


@lru_cache(maxsize=1)
def default_config() -> ProjectConfig:
    """Return the singleton default config loaded from project_config.json.

    Cached after the first call so the file is only read once per process.
    Use ProjectConfig.from_dict() for per-project overrides.
    """
    return ProjectConfig.load()


__all__ = ["ProjectConfig", "default_config"]
