"""ContinuityEngine — the public facade for the whole package.

Everything other teams need is here. One object, four methods:

    engine = ContinuityEngine()
    engine.ingest_script(script_json)        # team 1
    engine.ingest_footage(footage_json)      # team 2
    report = engine.analyse()                # -> team 4 / 5
    engine.apply_feedback(action)            # from the dashboard

Nothing below the facade is required reading for integration. Internals can be
reshaped freely as long as this signature holds.
"""

from __future__ import annotations

from typing import Any

from app.config import ProjectConfig, default_config
from app.feedback.human_feedback import FeedbackManager
from app.graph.builder import KnowledgeGraph
from app.graph.memory import ProductionMemory
from app.graph.storage import FactStore
from app.ingestion.dynamic_parser import DynamicParser
from app.ingestion.entity_matcher import EntityMatcher, keyword_semantic_matcher
from app.ingestion.normaliser import Normaliser
from app.models.schemas import (
    ContinuityReport,
    Fact,
    FactOverride,
    FeedbackAction,
    Issue,
    SourceType,
)
from app.reasoning.assumptions import AssumptionEngine
from app.reasoning.conflict_detector import ConflictDetector
from app.reporting.explanations import ExplanationWriter, LanguageModel
from app.reporting.suggestions import SuggestionWriter
from app.scoring.category_scores import CategoryScorer
from app.scoring.overall_score import overall_score, summarise


class ContinuityEngine:
    """Stateful per-project continuity engine.

    One instance holds one project's graph and memory. Construct with a
    `FactStore` to persist across processes; omit it for an in-memory run.
    """

    def __init__(
        self,
        config: ProjectConfig | None = None,
        store: FactStore | None = None,
        llm: LanguageModel | None = None,
    ) -> None:
        self.config = config or default_config()
        self.store = store

        self._normaliser = Normaliser(self.config)
        self._matcher = EntityMatcher(
            self.config, keyword_semantic_matcher(self.config.value_synonyms)
        )
        self._parser = DynamicParser(self.config, self._normaliser)

        self.graph = KnowledgeGraph(self.config, self._matcher)
        self.memory = ProductionMemory(self.graph, self.config)
        self.assumptions = AssumptionEngine(self.config)
        self.detector = ConflictDetector(
            self.graph, self.memory, self.config, self.assumptions, self._normaliser
        )
        self.feedback = FeedbackManager(self.graph, self.config)

        self._scorer = CategoryScorer(self.config, self.assumptions)
        self._explainer = ExplanationWriter(llm)
        self._suggester = SuggestionWriter(llm)
        self._issues: dict[str, Issue] = {}

    # -- ingestion ---------------------------------------------------------- #

    def ingest_script(self, payload: Any, extractor: str = "granite") -> list[Fact]:
        """Ingest structured script/call-sheet JSON from team 1."""
        return self._ingest(payload, SourceType.SCRIPT, extractor)

    def ingest_footage(self, payload: Any, extractor: str = "vision") -> list[Fact]:
        """Ingest structured footage observations from team 2."""
        return self._ingest(payload, SourceType.FOOTAGE, extractor)

    def ingest(
        self, payload: Any, source: SourceType, extractor: str | None = None
    ) -> list[Fact]:
        """Ingest any payload with an explicit source (call sheets, overrides)."""
        return self._ingest(payload, source, extractor)

    def _ingest(self, payload: Any, source: SourceType, extractor: str | None) -> list[Fact]:
        facts = self._parser.parse(payload, source, extractor)
        stored = self.graph.add_facts(facts)
        self.assumptions.ingest(stored, self.graph.timeline.sequence_of)
        if self.store is not None:
            self.store.save_facts(self.config.project_id, stored)
        return stored

    # -- analysis ----------------------------------------------------------- #

    def analyse(self, scene_id: str | None = None) -> ContinuityReport:
        """Run detection, scoring and reporting.

        With `scene_id`, only that scene is analysed; otherwise the whole
        project is. Re-running is safe and picks up any feedback applied since.
        """
        self._sync_dismissals()

        issues = (
            self.detector.detect_scene(scene_id)
            if scene_id is not None
            else self.detector.detect_all()
        )
        issues = self._carry_over_status(issues)
        issues = self._explainer.enrich_all(issues)
        issues = self._suggester.suggest_all(issues)

        category_scores, applied, mitigated = self._scorer.score(
            issues, self.graph.timeline.sequence_of
        )
        report = ContinuityReport(
            project_id=self.config.project_id,
            scene_id=scene_id,
            overall_score=overall_score(self.config, category_scores),
            category_scores=category_scores,
            issues=issues,
            temporary_assumptions=self.assumptions.assumptions,
            score_summary=summarise(issues, applied, mitigated),
            engine_version=self.config.engine_version,
        )

        self._issues = {i.issue_id: i for i in issues}
        if self.store is not None:
            self.store.save_issues(self.config.project_id, issues)
        return report

    # -- feedback ----------------------------------------------------------- #

    def apply_feedback(self, action: FeedbackAction) -> Issue | None:
        """Record a human decision on an issue. Re-run `analyse()` afterwards."""
        issue = self.feedback.apply(action, list(self._issues.values()))
        if issue is not None:
            self._issues[issue.issue_id] = issue
            if self.store is not None:
                self.store.save_feedback(self.config.project_id, action)
                self.store.save_issues(self.config.project_id, [issue])
        return issue

    def override_fact(self, override: FactOverride) -> Fact:
        """Record a human fact correction, outranking all AI-produced facts."""
        fact = self.feedback.override_fact(override)
        if self.store is not None:
            self.store.save_facts(self.config.project_id, [fact])
        return fact

    # -- introspection ------------------------------------------------------ #

    def issues(self) -> list[Issue]:
        return list(self._issues.values())

    def stats(self) -> dict[str, int]:
        return self.graph.stats()

    # -- internals ---------------------------------------------------------- #

    def _sync_dismissals(self) -> None:
        """Teach the detector which patterns the user has already accepted."""
        for entity_key, attribute, rule_id in self.feedback.dismissed_patterns():
            self.detector.dismiss_pattern(entity_key, attribute, rule_id)

    def _carry_over_status(self, issues: list[Issue]) -> list[Issue]:
        """Preserve human decisions across re-runs.

        Issue ids are regenerated each run, so decisions are matched on the
        stable (entity, attribute, rule, scene) signature instead.
        """
        previous = {
            (i.entity.key, i.attribute, i.type, i.scene_id): i for i in self._issues.values()
        }
        for issue in issues:
            match = previous.get((issue.entity.key, issue.attribute, issue.type, issue.scene_id))
            if match is not None:
                issue.issue_id = match.issue_id
                issue.status = match.status
        return issues
