"""Continuity rules and the registry that hosts them.

Adding a check means writing one function and decorating it — no edits to the
detector. That keeps the reasoning layer open for the rest of the team to
extend as teams 1 and 2 discover new attributes.

    @rule(id="lighting_mismatch", category=Category.LIGHTING, attributes=["lighting"])
    def lighting(ctx: RuleContext) -> RuleResult | None:
        ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from app.config import ProjectConfig
from app.graph.memory import SlotState
from app.ingestion.normaliser import Normaliser
from app.models.schemas import Category, Severity


@dataclass
class RuleContext:
    """Everything a rule may look at. Rules must not mutate any of it."""

    slot: SlotState
    config: ProjectConfig
    normaliser: Normaliser
    scene_id: str | None
    proximity: float = 1.0
    prior_occurrences: int = 0
    scene_has_footage: bool = False
    """Whether any footage observation exists for this scene at all.

    Without it, an absence rule cannot tell "the prop is missing" from
    "the scene has not been shot yet".
    """


@dataclass
class RuleResult:
    """A rule's verdict. The detector turns this into an Issue."""

    rule_id: str
    category: Category
    severity: Severity
    confidence: float
    explanation: str
    suggested_fix: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


RuleFn = Callable[[RuleContext], RuleResult | None]


@dataclass
class RegisteredRule:
    id: str
    category: Category
    fn: RuleFn
    attributes: tuple[str, ...]        # empty = applies to every attribute
    base_severity: Severity
    enabled: bool = True

    def applies_to(self, attribute: str) -> bool:
        return not self.attributes or attribute in self.attributes


class RuleRegistry:
    """Ordered collection of rules. One global default instance is provided."""

    def __init__(self) -> None:
        self._rules: dict[str, RegisteredRule] = {}

    def register(self, rule: RegisteredRule) -> None:
        self._rules[rule.id] = rule

    def get(self, rule_id: str) -> RegisteredRule | None:
        return self._rules.get(rule_id)

    def disable(self, rule_id: str) -> None:
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False

    def for_attribute(self, attribute: str) -> list[RegisteredRule]:
        return [r for r in self._rules.values() if r.enabled and r.applies_to(attribute)]

    def all(self) -> Iterable[RegisteredRule]:
        return list(self._rules.values())


REGISTRY = RuleRegistry()


def rule(
    *,
    id: str,
    category: Category,
    attributes: Iterable[str] = (),
    severity: Severity = Severity.MEDIUM,
    registry: RuleRegistry | None = None,
) -> Callable[[RuleFn], RuleFn]:
    """Register a continuity check. See module docstring for usage."""

    def decorator(fn: RuleFn) -> RuleFn:
        (registry or REGISTRY).register(
            RegisteredRule(
                id=id,
                category=category,
                fn=fn,
                attributes=tuple(attributes),
                base_severity=severity,
            )
        )
        return fn

    return decorator


# --------------------------------------------------------------------------- #
# Built-in rules
# --------------------------------------------------------------------------- #


def _mismatch(ctx: RuleContext) -> tuple[object, object] | None:
    """Shared precondition: a trusted expectation that the footage contradicts."""
    slot = ctx.slot
    if not slot.has_conflict_candidates:
        return None
    expected, observed = slot.expected, slot.observed
    assert expected is not None and observed is not None  # narrowed by the guard
    if ctx.normaliser.values_match(expected.value, observed.value):
        return None
    if observed.confidence < ctx.config.threshold("min_observation_confidence", 0.35):
        return None
    return expected.value, observed.value


def _confidence(ctx: RuleContext) -> float:
    """Detector confidence: how sure we are the *conflict* is real."""
    slot = ctx.slot
    expected, observed = slot.expected, slot.observed
    if expected is None or observed is None:
        return 0.0
    return round(min(1.0, expected.weight * observed.confidence * (0.5 + 0.5 * ctx.proximity)), 3)


@rule(id="hand_mismatch", category=Category.PROPS, attributes=["held_in_hand"], severity=Severity.MEDIUM)
def hand_mismatch(ctx: RuleContext) -> RuleResult | None:
    values = _mismatch(ctx)
    if values is None:
        return None
    expected, observed = values
    name = ctx.slot.entity_key.replace("_", " ")
    return RuleResult(
        rule_id="hand_mismatch",
        category=Category.PROPS,
        severity=Severity.MEDIUM,
        confidence=_confidence(ctx),
        explanation=(
            f"The script places the item in {name}'s {expected} hand, "
            f"while the footage shows it in the {observed} hand."
        ),
        suggested_fix=(
            f"Review the shot and move the item to the {expected} hand "
            "unless the change is intentional."
        ),
    )


@rule(id="prop_mismatch", category=Category.PROPS, attributes=["holds"], severity=Severity.MEDIUM)
def prop_mismatch(ctx: RuleContext) -> RuleResult | None:
    values = _mismatch(ctx)
    if values is None:
        return None
    expected, observed = values
    return RuleResult(
        rule_id="prop_mismatch",
        category=Category.PROPS,
        severity=Severity.MEDIUM,
        confidence=_confidence(ctx),
        explanation=f"Expected prop '{expected}' but the footage shows '{observed}'.",
        suggested_fix=f"Confirm which prop is correct for this scene; the script calls for '{expected}'.",
    )


@rule(id="missing_object", category=Category.PROPS, severity=Severity.HIGH)
def missing_object(ctx: RuleContext) -> RuleResult | None:
    """An expected prop with no observation at all in a scene that was filmed."""
    slot = ctx.slot
    if slot.attribute != "holds" or slot.expected is None or slot.observed is not None:
        return None
    if not ctx.scene_has_footage:
        return None  # scene not shot yet — absence proves nothing
    return RuleResult(
        rule_id="missing_object",
        category=Category.PROPS,
        severity=Severity.HIGH,
        confidence=round(slot.expected.weight, 3),
        explanation=(
            f"The script expects '{slot.expected.value}' in this scene, "
            "but it was not detected in the footage."
        ),
        suggested_fix=f"Check whether '{slot.expected.value}' is present in the shot.",
    )


@rule(id="costume_mismatch", category=Category.COSTUME, attributes=["wears"], severity=Severity.MEDIUM)
def costume_mismatch(ctx: RuleContext) -> RuleResult | None:
    values = _mismatch(ctx)
    if values is None:
        return None
    expected, observed = values
    name = ctx.slot.entity_key.replace("_", " ")
    return RuleResult(
        rule_id="costume_mismatch",
        category=Category.COSTUME,
        severity=Severity.MEDIUM,
        confidence=_confidence(ctx),
        explanation=(
            f"{name.title()} is expected to wear '{expected}' but the footage shows '{observed}', "
            "with no scripted costume change in between."
        ),
        suggested_fix=f"Confirm the wardrobe change was intentional, otherwise restore '{expected}'.",
    )


@rule(id="movement_mismatch", category=Category.MOVEMENT, attributes=["movement"], severity=Severity.LOW)
def movement_mismatch(ctx: RuleContext) -> RuleResult | None:
    values = _mismatch(ctx)
    if values is None:
        return None
    expected, observed = values
    return RuleResult(
        rule_id="movement_mismatch",
        category=Category.MOVEMENT,
        severity=Severity.LOW,
        confidence=_confidence(ctx),
        explanation=f"Expected movement '{expected}' but observed '{observed}'.",
        suggested_fix="Check the blocking against the script direction.",
    )


@rule(
    id="screen_direction_mismatch",
    category=Category.SPATIAL,
    attributes=["screen_position"],
    severity=Severity.MEDIUM,
)
def screen_direction_mismatch(ctx: RuleContext) -> RuleResult | None:
    values = _mismatch(ctx)
    if values is None:
        return None
    expected, observed = values
    return RuleResult(
        rule_id="screen_direction_mismatch",
        category=Category.SPATIAL,
        severity=Severity.MEDIUM,
        confidence=_confidence(ctx),
        explanation=(
            f"Screen position changed from '{expected}' to '{observed}' without a scripted move, "
            "which can break the 180-degree rule."
        ),
        suggested_fix="Verify the camera side and character blocking between shots.",
    )


@rule(id="location_mismatch", category=Category.SPATIAL, attributes=["location"], severity=Severity.HIGH)
def location_mismatch(ctx: RuleContext) -> RuleResult | None:
    values = _mismatch(ctx)
    if values is None:
        return None
    expected, observed = values
    return RuleResult(
        rule_id="location_mismatch",
        category=Category.SPATIAL,
        severity=Severity.HIGH,
        confidence=_confidence(ctx),
        explanation=f"Scene is scripted at '{expected}' but the footage suggests '{observed}'.",
        suggested_fix=f"Confirm the shooting location matches the scripted '{expected}'.",
    )


@rule(id="lighting_mismatch", category=Category.LIGHTING, attributes=["lighting"], severity=Severity.LOW)
def lighting_mismatch(ctx: RuleContext) -> RuleResult | None:
    values = _mismatch(ctx)
    if values is None:
        return None
    expected, observed = values
    return RuleResult(
        rule_id="lighting_mismatch",
        category=Category.LIGHTING,
        severity=Severity.LOW,
        confidence=_confidence(ctx),
        explanation=f"Lighting is described as '{expected}' but observed as '{observed}'.",
        suggested_fix="Check the lighting setup against neighbouring scenes.",
    )


@rule(id="custom_attribute_conflict", category=Category.OTHER, severity=Severity.LOW)
def custom_attribute_conflict(ctx: RuleContext) -> RuleResult | None:
    """Catch-all so novel attributes from teams 1 and 2 are still checked."""
    known = {r.attributes for r in REGISTRY.all() if r.attributes}
    if any(ctx.slot.attribute in attrs for attrs in known):
        return None
    values = _mismatch(ctx)
    if values is None:
        return None
    expected, observed = values
    return RuleResult(
        rule_id="custom_attribute_conflict",
        category=Category.OTHER,
        severity=Severity.LOW,
        confidence=_confidence(ctx),
        explanation=(
            f"'{ctx.slot.attribute}' was expected to be '{expected}' but observed as '{observed}'."
        ),
        suggested_fix=f"Review '{ctx.slot.attribute}' for this scene.",
    )
