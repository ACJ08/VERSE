"""Per-category continuity scoring.

Each issue subtracts from its category's score. The penalty is scaled by how
much we actually believe the issue: a low-confidence detection from a
low-trust source barely moves the number, which is what keeps the score
trustworthy enough for a human to act on.
"""

from __future__ import annotations

from collections import defaultdict

from app.config import ProjectConfig
from app.models.schemas import Category, Issue, IssueStatus
from app.reasoning.assumptions import AssumptionEngine


class CategoryScorer:
    """Computes category scores and annotates each issue with its impact."""

    def __init__(self, config: ProjectConfig, assumptions: AssumptionEngine | None = None) -> None:
        self._config = config
        self._assumptions = assumptions

    def score(
        self, issues: list[Issue], sequence_of=lambda scene_id: 0
    ) -> tuple[dict[str, float], int, int]:
        """Return (category scores, penalties applied, issues mitigated).

        Mutates `issue.score_impact` so the UI can show why a score dropped.
        """
        totals: dict[str, float] = defaultdict(float)
        applied = 0
        mitigated = 0

        for issue in issues:
            if issue.status is IssueStatus.DISMISSED:
                issue.score_impact = 0.0
                continue  # accepted as intentional — no penalty, still in history

            penalty = self._penalty(issue, sequence_of(issue.scene_id))
            if issue.mitigated_by:
                mitigated += 1
            if penalty > 0:
                applied += 1

            issue.score_impact = round(penalty, 2)
            totals[issue.category.value] += penalty

        scores = {category: 100.0 for category in self._config.categories}
        for category, penalty in totals.items():
            scores[category] = max(0.0, round(100.0 - penalty, 1))
        return scores, applied, mitigated

    def _penalty(self, issue: Issue, sequence: int) -> float:
        base = self._config.severity_penalty(issue.severity)

        # Belief scaling. `issue.confidence` already folds in source trust,
        # observation confidence and narrative proximity (see rules._confidence),
        # so multiplying by trust again here would penalise it twice.
        penalty = base * issue.confidence

        # Repetition compounds — the same error across scenes is worse.
        if issue.occurrences > 1:
            penalty *= 1.0 + 0.25 * (issue.occurrences - 1)

        # Narrative justification softens the blow.
        if self._assumptions is not None:
            penalty *= self._assumptions.mitigation(issue.category, sequence, issue.entity.key)

        # A human who confirmed the issue removes all doubt.
        if issue.status is IssueStatus.CONFIRMED:
            penalty = base * (1.0 + 0.25 * (issue.occurrences - 1))

        return max(0.0, penalty)


def weighted_categories(config: ProjectConfig, scores: dict[str, float]) -> dict[Category, float]:
    """Helper for the overall score: drop untouched categories from the mean."""
    return {
        Category(name) if name in {c.value for c in Category} else Category.OTHER: value
        for name, value in scores.items()
        if config.category_weight(name) > 0
    }
