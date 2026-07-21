"""Suggested fixes.

Rule-based logic decides *what* the correction is; the LLM only decides how to
phrase it. Suggestions are always recommendations — the engine never acts.
"""

from __future__ import annotations

from app.models.schemas import Issue, Severity
from app.reporting.explanations import LanguageModel, _safe_call

# Fallback templates by rule id, used when a rule supplies no suggestion.
_TEMPLATES: dict[str, str] = {
    "hand_mismatch": "Reshoot or verify the hand holding the prop against the script.",
    "prop_mismatch": "Confirm the correct prop for this scene with the art department.",
    "missing_object": "Check whether the scripted prop is present in the shot.",
    "costume_mismatch": "Confirm the wardrobe change with the costume department.",
    "movement_mismatch": "Review the blocking against the scripted stage direction.",
    "screen_direction_mismatch": "Verify camera side and eyeline continuity for this sequence.",
    "location_mismatch": "Confirm the shooting location matches the scripted setting.",
    "lighting_mismatch": "Compare the lighting setup with adjacent scenes.",
}

_PRIORITY_PREFIX = {
    Severity.CRITICAL: "Before the next setup: ",
    Severity.HIGH: "Priority: ",
    Severity.MEDIUM: "",
    Severity.LOW: "When convenient: ",
}


class SuggestionWriter:
    def __init__(self, llm: LanguageModel | None = None) -> None:
        self._llm = llm

    def suggest(self, issue: Issue) -> Issue:
        base = issue.suggested_fix or _TEMPLATES.get(
            issue.type, f"Review '{issue.attribute}' continuity for this scene."
        )
        text = _PRIORITY_PREFIX[issue.severity] + base

        if issue.mitigated_by:
            text += " Narrative context may already explain this — confirm before changing anything."

        if self._llm is not None:
            polished = _safe_call(self._llm, _prompt(issue, text))
            if polished:
                text = polished

        issue.suggested_fix = text
        return issue

    def suggest_all(self, issues: list[Issue]) -> list[Issue]:
        return [self.suggest(issue) for issue in issues]


def _prompt(issue: Issue, suggestion: str) -> str:
    return (
        "Rephrase this film continuity recommendation as one polite, actionable "
        "sentence for a script supervisor. Do not add new instructions.\n\n"
        f"Issue: {issue.explanation}\nRecommendation: {suggestion}"
    )
