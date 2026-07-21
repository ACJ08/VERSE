"""Overall continuity score.

A configurable weighted mean of the category scores. Categories with no issues
still count — a production that is clean everywhere should score 100.
"""

from __future__ import annotations

from app.config import ProjectConfig
from app.models.schemas import Issue, IssueStatus, ScoreSummary, Severity


def overall_score(config: ProjectConfig, category_scores: dict[str, float]) -> float:
    if not category_scores:
        return 100.0
    numerator = 0.0
    denominator = 0.0
    for category, score in category_scores.items():
        weight = config.category_weight(category)
        numerator += score * weight
        denominator += weight
    if denominator == 0:
        return 100.0
    return round(numerator / denominator, 1)


def summarise(issues: list[Issue], applied: int, mitigated: int) -> ScoreSummary:
    """One human sentence explaining the score, for the dashboard header."""
    active = [i for i in issues if i.status is not IssueStatus.DISMISSED]
    if not active:
        return ScoreSummary(
            main_reason="No continuity issues were detected.",
            penalties_applied=applied,
            issues_mitigated=mitigated,
        )

    worst = max(active, key=lambda i: (_severity_rank(i.severity), i.score_impact))
    categories = sorted({i.category.value for i in active})
    category_text = categories[0] if len(categories) == 1 else ", ".join(categories)
    plural = "issue" if len(active) == 1 else "issues"

    reason = (
        f"{len(active)} continuity {plural} reduced the {category_text} "
        f"score, led by a {worst.severity.value} {worst.type.replace('_', ' ')}."
    )
    if mitigated:
        reason += f" {mitigated} were softened by narrative context."
    return ScoreSummary(
        main_reason=reason, penalties_applied=applied, issues_mitigated=mitigated
    )


def _severity_rank(severity: Severity) -> int:
    return [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL].index(severity)
