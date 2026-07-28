"""
VERSE – Continuity Script Intelligence
app/schemas.py (Legacy Backwards Compatibility Layer)

Preserves original legacy model declarations by re-exporting from app.schemas.
"""

from app.schemas.continuity import (
    Character,
    Prop,
    Lighting,
    SceneMetadata,
    ContinuityNote,
    SceneContinuity,
)

__all__ = [
    "Character",
    "Prop",
    "Lighting",
    "SceneMetadata",
    "ContinuityNote",
    "SceneContinuity",
]