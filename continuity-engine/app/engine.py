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
from app.services.extraction import GraniteFactExtractor


class ContinuityEngine:
    """Stateful per-project continuity engine.

    One instance holds one project's graph and memory. Construct with a
    `FactStore` to persist across processes; omit it for an in-memory run.

    Parameters
    ----------
    config:
        Project-level tunables (weights, thresholds, aliases). Defaults to
        ``default_config()`` when omitted.
    store:
        SQLite-backed FactStore for persistence across restarts. Omit for an
        in-memory-only run (tests, one-shot scripts).
    llm:
        Optional LanguageModel (e.g. WatsonxAdapter). Forwarded to
        AssumptionEngine (trigger classification), ExplanationWriter (NL
        explanations), and SuggestionWriter (NL fix suggestions).  When None
        all three fall back to their rule-based paths — reports are still
        complete and accurate.
    semantic_matcher:
        Optional callable ``(left: str, right: str) -> float`` returning a
        similarity score in [0, 1].  Forwarded to EntityMatcher as its AI
        fallback for resolving "Elena" == "Elena Chen".  When None the engine
        uses keyword synonyms + fuzzy string matching only.
    """

    def __init__(
        self,
        config: ProjectConfig | None = None,
        store: FactStore | None = None,
        llm: LanguageModel | None = None,
        semantic_matcher=None,
    ) -> None:
        self.config = config or default_config()
        self.store = store

        self._normaliser = Normaliser(self.config)
        # Prefer the Granite-backed semantic matcher when available; fall back to
        # the keyword-synonym table that ships with the default config.
        _sm = semantic_matcher or keyword_semantic_matcher(self.config.value_synonyms)
        self._matcher = EntityMatcher(self.config, _sm)
        self._parser = DynamicParser(self.config, self._normaliser)

        # Granite fact extractor — used when extractor == "granite" and the
        # Ollama/local Granite client is reachable.  Failures are silently ignored
        # so the engine always produces results regardless of LLM availability.
        self._granite_extractor: GraniteFactExtractor | None = self._build_granite_extractor()

        self.graph = KnowledgeGraph(self.config, self._matcher)
        self.memory = ProductionMemory(self.graph, self.config)
        self.assumptions = AssumptionEngine(self.config, llm=llm)
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

        # If the caller requested "granite" extraction and a local Granite server
        # is available, augment the parsed facts with Granite-extracted facts for
        # any raw scene text blocks present in the payload.
        if extractor == "granite" and self._granite_extractor is not None:
            extra = self._extract_granite_facts(payload, source)
            # Merge: prefer already-parsed facts; add Granite extras that aren't duplicates.
            existing_ids = {(f.entity.key, f.attribute, f.scene_id) for f in facts}
            for f in extra:
                if (f.entity.key, f.attribute, f.scene_id) not in existing_ids:
                    facts.append(f)

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

        # Repetition counts are rebuilt per pass so `analyse()` is idempotent.
        self.detector.reset()
        if scene_id is not None:
            self.detector.seed_history(
                [i for i in self._issues.values() if i.scene_id != scene_id]
            )

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

    # -- Granite extractor helpers ------------------------------------------- #
    @staticmethod
    def _build_granite_extractor() -> "GraniteFactExtractor | None":
        """Try to create a GraniteFactExtractor backed by the local Granite/Ollama server.

        Returns None (silently) when the server is not reachable or the library
        is not installed — the engine continues without Granite augmentation.
        """
        try:
            from app.services.granite_client import GraniteClient
            return GraniteFactExtractor(GraniteClient())
        except Exception:
            return None

    def _extract_granite_facts(self, payload: Any, source: SourceType) -> list[Fact]:
        """Extract additional facts from scene text blobs using the Granite client.

        Walks the payload looking for "action" or "text" string fields inside
        scene objects and runs the Granite extractor on each.
        """
        import re

        facts: list[Fact] = []
        if not isinstance(payload, dict):
            return facts

        scenes = payload.get("scenes") or []
        if not isinstance(scenes, list):
            return facts

        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            scene_id = scene.get("scene_id") or scene.get("id") or None
            text_blob = scene.get("action") or scene.get("text") or ""
            if not isinstance(text_blob, str) or not text_blob.strip():
                continue
            try:
                extracted = self._granite_extractor.extract_scene_facts(  # type: ignore[union-attr]
                    scene_text=text_blob,
                    scene_id=scene_id,
                )
                facts.extend(extracted)
            except Exception:
                pass  # Granite call failed — skip augmentation for this scene

        return facts
    @property
    def normaliser(self) -> Normaliser:
        """Value/attribute canonicaliser — needed to ask "do these two agree?"."""
        return self._normaliser

    @property
    def scorer(self) -> CategoryScorer:
        """The project's scorer, so derived views score the same way reports do."""
        return self._scorer

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
            (i.entity.key, i.attribute, i.type, i.scene_id): i
            for i in self._issues.values()
        }
        for issue in issues:
            match = previous.get((issue.entity.key, issue.attribute, issue.type, issue.scene_id))
            if match is not None:
                issue.issue_id = match.issue_id
                issue.status = match.status
        return issues
