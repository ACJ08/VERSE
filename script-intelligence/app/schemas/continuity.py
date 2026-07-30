"""
VERSE Schemas - Scene Continuity Models.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

SEVERITY_VALUES = {"LOW", "MEDIUM", "HIGH"}
HAND_VALUES = {"left", "right", "both", "none"}
INT_EXT_VALUES = {"INT.", "EXT.", "INT./EXT.", "I/E."}


class Character(BaseModel):
    """A character present in a screenplay scene."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Character's full name as written in the script.")
    costume: Optional[str] = Field(
        None,
        description="Wardrobe or costume description for continuity tracking.",
    )
    position: Optional[str] = Field(
        None,
        description="Spatial position in the frame/set (e.g. 'standing by the door').",
    )
    movement: Optional[str] = Field(
        None,
        description="Physical action or movement (e.g. 'crosses to the window').",
    )
    emotional_state: Optional[str] = Field(
        None,
        description="Inferred emotional or psychological state in this scene.",
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Character name must not be blank.")
        return v.strip().upper()


class Prop(BaseModel):
    """A physical prop or object that appears in a scene."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Object or prop name.")
    hand_usage: Optional[str] = Field(
        None,
        description="Which hand carries/uses the prop: left, right, both, or none.",
    )
    state: Optional[str] = Field(
        None,
        description="Physical condition or state of the prop (e.g. 'broken', 'open').",
    )
    owner: Optional[str] = Field(
        None,
        description="Character who owns or holds the prop, if identifiable.",
    )

    @field_validator("hand_usage")
    @classmethod
    def normalise_hand_usage(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        lower = v.strip().lower()
        if lower and lower not in HAND_VALUES:
            for allowed in HAND_VALUES:
                if allowed in lower:
                    return allowed
        return lower or None


class Lighting(BaseModel):
    """Lighting conditions for a scene."""

    model_config = ConfigDict(populate_by_name=True)

    description: Optional[str] = Field(
        None,
        description="Free-text description of the lighting setup.",
    )
    source: Optional[str] = Field(
        None,
        description="Primary light source (e.g. 'practical lamp', 'sunlight', 'neon sign').",
    )
    mood: Optional[str] = Field(
        None,
        description="Emotional tone conveyed by the lighting (e.g. 'tense', 'romantic').",
    )
    time_of_day: Optional[str] = Field(
        None,
        description="DAY | NIGHT | DAWN | DUSK as written in the scene heading.",
    )


class SceneMetadata(BaseModel):
    """Header-level information parsed from a scene slug line."""

    model_config = ConfigDict(populate_by_name=True)

    scene_id: str = Field(
        ...,
        description="Sequential scene identifier (e.g. 'SCENE_001').",
    )
    heading: Optional[str] = Field(
        None,
        description="Full slug line exactly as it appears in the script.",
    )
    interior_exterior: Optional[str] = Field(
        None,
        description="INT., EXT., or INT./EXT.",
    )
    location: Optional[str] = Field(
        None,
        description="Primary location name extracted from the scene heading.",
    )
    sub_location: Optional[str] = Field(
        None,
        description="Sub-location if specified.",
    )
    time: Optional[str] = Field(
        None,
        description="Time of day as written in the heading (DAY, NIGHT, etc.).",
    )


class ContinuityNote(BaseModel):
    """A single continuity observation or warning for a scene."""

    model_config = ConfigDict(populate_by_name=True)

    note: str = Field(
        ...,
        description="Human-readable description of the continuity concern.",
    )
    severity: Optional[str] = Field(
        None,
        description="Risk level: LOW | MEDIUM | HIGH.",
    )
    category: Optional[str] = Field(
        None,
        description="Type of concern: WARDROBE | PROP | LIGHTING | MOVEMENT | DIALOGUE | OTHER.",
    )
    affected_characters: Optional[List[str]] = Field(
        None,
        description="Names of characters involved in this continuity issue.",
    )

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        upper = v.strip().upper()
        if upper not in SEVERITY_VALUES:
            return "LOW"
        return upper


class SceneContinuity(BaseModel):
    """Structured continuity data extracted for a single screenplay scene."""

    model_config = ConfigDict(populate_by_name=True)

    metadata: SceneMetadata = Field(
        ...,
        description="Scene header information (slug line, location, time).",
    )
    characters: List[Character] = Field(
        default_factory=list,
        description="All characters present in the scene.",
    )
    props: List[Prop] = Field(
        default_factory=list,
        description="All significant props or objects in the scene.",
    )
    lighting: Optional[Lighting] = Field(
        None,
        description="Lighting description and mood.",
    )
    continuity_notes: List[ContinuityNote] = Field(
        default_factory=list,
        description="Continuity warnings or observations flagged by the AI.",
    )
    confidence_score: Optional[float] = Field(
        1.0,
        description="Extraction confidence score (0.0 to 1.0).",
    )
    action: Optional[str] = Field(
        None,
        description=(
            "Scene action prose, excluding the slug line. Downstream continuity "
            "reasoning reads this to detect scripted state changes ('SARAH removes "
            "her blazer') and narrative events that may explain a discrepancy "
            "('the crowd panics'). Truncated; use raw_scene_text for the full block."
        ),
    )
    raw_scene_text: Optional[str] = Field(
        None,
        description="The original scene text that was analysed.",
        exclude=True,
    )

    @model_validator(mode="after")
    def deduplicate_characters(self) -> "SceneContinuity":
        """Remove duplicate character entries (same name)."""
        seen: set[str] = set()
        unique: list[Character] = []
        for char in self.characters:
            if char.name not in seen:
                seen.add(char.name)
                unique.append(char)
        self.characters = unique
        return self
