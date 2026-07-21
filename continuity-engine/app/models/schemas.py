"""Shared contracts for the VERSE continuity engine.

Every boundary in this package speaks in these types. Other teams should import
from here rather than passing raw dicts around:

    from app.models.schemas import ContinuityReport, Fact, Issue

The JSON shapes produced by ``model_dump(mode="json")`` are the integration
contract with the Script AI (team 1), Vision (team 2) and Backend (team 5).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


class SourceType(str, Enum):
    """Where a fact came from. Drives the default trust ordering."""

    HUMAN = "human"
    SCRIPT = "script"
    CALL_SHEET = "call_sheet"
    FOOTAGE = "footage"
    AI_INFERENCE = "ai_inference"


class EntityType(str, Enum):
    """Known node types. Unknown types are kept as CUSTOM with the raw label."""

    SCENE = "scene"
    CHARACTER = "character"
    PROP = "prop"
    COSTUME = "costume"
    LOCATION = "location"
    ACTION = "action"
    LIGHTING = "lighting"
    MOVEMENT = "movement"
    CUSTOM = "custom"


class Category(str, Enum):
    """Scoring buckets. Extendable via project config `custom_categories`."""

    PROPS = "props"
    COSTUME = "costume"
    MOVEMENT = "movement"
    SPATIAL = "spatial"
    NARRATIVE = "narrative"
    LIGHTING = "lighting"
    OTHER = "other"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"       # intentional — stops future penalties
    RESOLVED = "resolved"


# --------------------------------------------------------------------------- #
# Facts
# --------------------------------------------------------------------------- #


class EntityRef(BaseModel):
    """A production element. `key` is the normalised identity used for matching."""

    model_config = ConfigDict(frozen=True)

    type: EntityType = EntityType.CUSTOM
    name: str
    key: str = ""
    raw_type: str | None = None  # original label when type is CUSTOM

    def model_post_init(self, _ctx: Any) -> None:
        if not self.key:
            object.__setattr__(self, "key", normalise_key(self.name))


class SourceRef(BaseModel):
    """Provenance for a fact — always shown to the user in the report."""

    type: SourceType
    reference: str = ""          # "Scene 12", "00:14.2", "call_sheet_p3"
    extractor: str | None = None  # "granite-3.1", "opencv-yolo", ...


class FactEdit(BaseModel):
    """One entry in a fact's edit history. Facts are never silently overwritten."""

    at: datetime = Field(default_factory=_utcnow)
    actor: str = "system"
    previous_value: Any = None
    reason: str = ""


class Fact(BaseModel):
    """A single atomic claim: <entity> has <attribute> = <value>, per <source>.

    Conflicting facts coexist. The engine resolves them at comparison time using
    trust levels rather than dropping data at ingestion time.
    """

    fact_id: str
    entity: EntityRef
    attribute: str                     # canonical, e.g. "held_in_hand"
    value: Any
    raw_attribute: str | None = None   # original key from the producing team
    raw_value: Any = None              # original value before normalisation

    scene_id: str | None = None
    sequence: int | None = None        # screenplay order, not shooting order
    timestamp: str | None = None       # footage time, e.g. "00:14.2"

    source: SourceRef
    confidence: float = 1.0
    trust: float = 0.0                 # filled by the trust policy at ingestion
    human_confirmed: bool = False
    history: list[FactEdit] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def weight(self) -> float:
        """Combined authority of this fact. Human confirmation always wins."""
        return 1.0 if self.human_confirmed else self.trust * self.confidence


# --------------------------------------------------------------------------- #
# Assumptions
# --------------------------------------------------------------------------- #


class TemporaryAssumption(BaseModel):
    """A soft, expiring belief derived from narrative text.

    Example: "the crowd panics and rushes through the shop" implies objects may
    have moved. Assumptions dampen penalties; they never override a fact.
    """

    assumption_id: str
    description: str
    scene_id: str | None = None
    created_at_sequence: int = 0
    expires_after_scenes: int = 2
    confidence: float = 0.5
    source_text: str = ""
    affects_categories: list[Category] = Field(default_factory=list)
    affects_entities: list[str] = Field(default_factory=list)  # entity keys, empty = all
    active: bool = True
    contradicted_by: str | None = None

    def is_active_at(self, sequence: int) -> bool:
        if not self.active:
            return False
        return sequence <= self.created_at_sequence + self.expires_after_scenes


# --------------------------------------------------------------------------- #
# Issues & reports
# --------------------------------------------------------------------------- #


class ObservationRef(BaseModel):
    """The `expected` / `observed` half of an issue, with its provenance.

    `source` is None when the half is an absence — a missing prop has no
    observation to cite.
    """

    value: Any = None
    source: SourceType | None = None
    source_reference: str = ""
    confidence: float = 1.0


class Issue(BaseModel):
    issue_id: str
    category: Category
    type: str                       # rule id, e.g. "hand_mismatch"
    severity: Severity
    confidence: float

    entity: EntityRef
    attribute: str
    scene_id: str | None = None

    expected: ObservationRef
    observed: ObservationRef

    explanation: str = ""
    suggested_fix: str = ""
    status: IssueStatus = IssueStatus.PENDING_REVIEW

    occurrences: int = 1                     # repeats across scenes escalate severity
    related_scene_ids: list[str] = Field(default_factory=list)
    mitigated_by: list[str] = Field(default_factory=list)  # assumption ids
    score_impact: float = 0.0
    supporting_fact_ids: list[str] = Field(default_factory=list)


class ScoreSummary(BaseModel):
    main_reason: str = ""
    penalties_applied: int = 0
    issues_mitigated: int = 0


class ContinuityReport(BaseModel):
    """The engine's output. This is what team 4 renders and team 5 persists."""

    project_id: str
    scene_id: str | None = None
    overall_score: float = 100.0
    category_scores: dict[str, float] = Field(default_factory=dict)
    issues: list[Issue] = Field(default_factory=list)
    temporary_assumptions: list[TemporaryAssumption] = Field(default_factory=list)
    score_summary: ScoreSummary = Field(default_factory=ScoreSummary)
    generated_at: datetime = Field(default_factory=_utcnow)
    engine_version: str = "0.1.0"


# --------------------------------------------------------------------------- #
# Feedback
# --------------------------------------------------------------------------- #


class FeedbackAction(BaseModel):
    """A human decision arriving from the dashboard via team 5."""

    issue_id: str
    action: Literal["confirm", "dismiss", "resolve", "reopen"]
    actor: str = "user"
    note: str = ""
    at: datetime = Field(default_factory=_utcnow)


class FactOverride(BaseModel):
    """A human-authored fact correction. Outranks every AI-produced fact."""

    entity_key: str
    attribute: str
    value: Any
    scene_id: str | None = None
    actor: str = "user"
    reason: str = ""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def normalise_key(name: str) -> str:
    """Lowercase, collapse whitespace and punctuation. Used for entity identity."""
    import re

    cleaned = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
    return cleaned or "unknown"
