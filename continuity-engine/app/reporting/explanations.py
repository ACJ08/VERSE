"""Explanation generation.

Rules already produce a plain-language explanation. This module enriches it
with provenance so the dashboard can always answer "why do you think that?",
and exposes an optional LLM hook for nicer phrasing.

The rule-based text is always the fallback: if the LLM is unavailable or
returns nothing, the report is still complete and accurate.
"""

from __future__ import annotations

from typing import Callable, Protocol

from app.models.schemas import Issue


class LanguageModel(Protocol):
    """Minimal interface so watsonx/Granite can be dropped in without changes."""

    def __call__(self, prompt: str) -> str: ...


class ExplanationWriter:
    def __init__(self, llm: LanguageModel | None = None) -> None:
        self._llm = llm

    def enrich(self, issue: Issue) -> Issue:
        """Attach source citations, and optionally an LLM-polished explanation."""
        issue.explanation = self._with_sources(issue)
        if self._llm is not None:
            polished = _safe_call(self._llm, _prompt(issue))
            if polished:
                issue.explanation = polished
        return issue

    def enrich_all(self, issues: list[Issue]) -> list[Issue]:
        return [self.enrich(issue) for issue in issues]

    @staticmethod
    def _with_sources(issue: Issue) -> str:
        parts = [issue.explanation.rstrip(".") + "."]
        expected, observed = issue.expected, issue.observed
        if expected.source is not None:
            parts.append(
                f"Expected value from {expected.source.value}"
                + (f" ({expected.source_reference})" if expected.source_reference else "")
                + "."
            )
        if observed.source is not None:
            parts.append(
                f"Observed in {observed.source.value}"
                + (f" at {observed.source_reference}" if observed.source_reference else "")
                + f" with {observed.confidence:.0%} confidence."
            )
        if issue.occurrences > 1:
            parts.append(f"Seen in {issue.occurrences} scenes ({', '.join(issue.related_scene_ids)}).")
        if issue.mitigated_by:
            parts.append(
                "Score impact was reduced because narrative context may explain the change."
            )
        return " ".join(parts)


def _prompt(issue: Issue) -> str:
    return (
        "Rewrite this film continuity note for a script supervisor in two clear "
        "sentences. Keep every fact and source unchanged. Do not speculate.\n\n"
        f"{issue.explanation}"
    )


def _safe_call(fn: Callable[[str], str], prompt: str) -> str | None:
    """LLM failures must never break a report."""
    try:
        result = fn(prompt)
    except Exception:  # noqa: BLE001 - degrade to rule-based text
        return None
    return result.strip() if isinstance(result, str) and result.strip() else None
