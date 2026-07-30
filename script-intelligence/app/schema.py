"""
VERSE – Continuity Script Intelligence
app/schema.py (Backwards Compatibility Module)

Re-exports all Pydantic v2 data models from app.schemas.
"""

from app.schemas.continuity import (
    Character,
    Prop,
    Lighting,
    SceneMetadata,
    ContinuityNote,
    SceneContinuity,
    SEVERITY_VALUES,
    HAND_VALUES,
    INT_EXT_VALUES,
)
from app.schemas.call_sheet import CallSheetData
from app.schemas.requests import AnalyseSceneRequest
from app.schemas.responses import (
    FileUploadResponse,
    ParseScriptResponse,
    AnalyseScriptResponse,
    CallSheetResponse,
    HealthResponse,
)

__all__ = [
    "Character",
    "Prop",
    "Lighting",
    "SceneMetadata",
    "ContinuityNote",
    "SceneContinuity",
    "SEVERITY_VALUES",
    "HAND_VALUES",
    "INT_EXT_VALUES",
    "CallSheetData",
    "AnalyseSceneRequest",
    "FileUploadResponse",
    "ParseScriptResponse",
    "AnalyseScriptResponse",
    "CallSheetResponse",
    "HealthResponse",
]
