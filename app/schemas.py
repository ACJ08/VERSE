from pydantic import BaseModel, Field
from typing import List, Optional


class Character(BaseModel):
    name: str = Field(..., description="Character name")
    costume: Optional[str] = Field(
        None,
        description="Character costume or wardrobe"
    )
    position: Optional[str] = Field(
        None,
        description="Character position in scene"
    )
    movement: Optional[str] = Field(
        None,
        description="Character movement/action"
    )


class Prop(BaseModel):
    name: str = Field(..., description="Object or prop name")
    hand_usage: Optional[str] = Field(
        None,
        description="Left hand, right hand, both hands, etc."
    )
    state: Optional[str] = Field(
        None,
        description="Condition of object"
    )


class Lighting(BaseModel):
    description: Optional[str] = None
    source: Optional[str] = None
    mood: Optional[str] = None


class SceneMetadata(BaseModel):
    scene_id: str

    heading: Optional[str] = Field(
        None,
        description="INT/EXT scene heading"
    )

    location: Optional[str] = None

    time: Optional[str] = None


class ContinuityNote(BaseModel):
    note: str

    severity: Optional[str] = Field(
        None,
        description="LOW, MEDIUM, HIGH"
    )


class SceneContinuity(BaseModel):

    metadata: SceneMetadata

    characters: List[Character] = []

    props: List[Prop] = []

    lighting: Optional[Lighting] = None

    continuity_notes: List[ContinuityNote] = []
    