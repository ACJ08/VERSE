"""
VERSE – Continuity Script Intelligence
app/schema.py

Pydantic v2 data models for the entire continuity pipeline.

Design principles
-----------------
* Every field carries a human-readable description (surfaced in OpenAPI).
* Optional fields default to ``None`` so partial Granite responses are
  accepted gracefully.
* Aggregate response models wrap the per-scene models so that the API
  always returns a well-typed, self-describing JSON document.
* ``model_config`` is set to ``populate_by_name=True`` so we can accept
  both snake_case and camelCase payloads where needed.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic import ConfigDict


# ---------------------------------------------------------------------------
# Enumeration-like string constants used in validator logic
# ---------------------------------------------------------------------------

SEVERITY_VALUES = {"LOW", "MEDIUM", "HIGH"}
HAND_VALUES = {"left", "right", "both", "none"}
INT_EXT_VALUES = {"INT.", "EXT.", "INT./EXT.", "I/E."}


# ===========================================================================
# Scene-level sub-models
# ===========================================================================

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
        if not v.strip():
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
            # Attempt a fuzzy match rather than rejecting outright
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
        description="Sequential scene identifier (e.g. 'SCENE_01').",
    )
    heading: Optional[str] = Field(
        None,
        description="Full slug line exactly as it appears in the script (e.g. 'INT. KITCHEN - NIGHT').",
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
        description="Sub-location if specified (e.g. 'LIVING ROOM' within 'SARAH'S APARTMENT').",
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
            return "LOW"  # graceful fallback instead of raising
        return upper


# ===========================================================================
# Primary per-scene continuity model
# ===========================================================================

class SceneContinuity(BaseModel):
    """
    Structured continuity data extracted for a single screenplay scene.

    This is the core output unit produced by the Granite analysis pipeline
    and stored / returned by the API.
    """

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
    raw_scene_text: Optional[str] = Field(
        None,
        description="The original scene text that was analysed (omitted in list responses).",
        exclude=True,  # excluded from serialisation by default
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


# ===========================================================================
# API request / response envelope models
# ===========================================================================

class AnalyseSceneRequest(BaseModel):
    """Request body for the ``/analyse-scene`` endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    scene_text: str = Field(
        ...,
        min_length=1,
        description="Raw text of a single screenplay scene.",
    )
    scene_id: Optional[str] = Field(
        None,
        description="Optional caller-supplied scene identifier.",
    )


class AnalyseScriptResponse(BaseModel):
    """Top-level response envelope for full-script analysis."""

    model_config = ConfigDict(populate_by_name=True)

    filename: str = Field(..., description="Name of the uploaded file.")
    scene_count: int = Field(..., description="Total number of scenes detected.")
    scenes: List[SceneContinuity] = Field(
        default_factory=list,
        description="Per-scene structured continuity data.",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Non-fatal errors encountered during processing (e.g. individual scene failures).",
    )


class ParseScriptResponse(BaseModel):
    """Response for simple script parsing (no AI analysis)."""

    model_config = ConfigDict(populate_by_name=True)

    filename: str
    scene_count: int
    extracted_text_path: str
    first_scene_preview: Optional[str] = None


class HealthResponse(BaseModel):
    """API health-check response."""

    status: str = "ok"
    version: str
    granite_configured: bool = Field(
        ...,
        description="True when Watsonx credentials are detected in the environment.",
    )
