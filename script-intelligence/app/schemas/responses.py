"""
VERSE Schemas - API Response Envelope Models.
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.continuity import SceneContinuity
from app.schemas.call_sheet import CallSheetData


class FileUploadResponse(BaseModel):
    """Response envelope for script upload."""

    model_config = ConfigDict(populate_by_name=True)

    message: str = Field("Script uploaded successfully.", description="Status message.")
    filename: str = Field(..., description="Original filename.")
    path: str = Field(..., description="Path on disk where file was saved.")


class ParseScriptResponse(BaseModel):
    """Response envelope for simple script parsing without AI."""

    model_config = ConfigDict(populate_by_name=True)

    filename: str = Field(..., description="Uploaded filename.")
    scene_count: int = Field(..., description="Total scenes split.")
    extracted_text_path: str = Field(..., description="Path to persisted extracted text file.")
    first_scene_preview: Optional[str] = Field(None, description="Preview snippet of the first scene.")


class AnalyseScriptResponse(BaseModel):
    """Top-level response envelope for full-script AI continuity analysis."""

    model_config = ConfigDict(populate_by_name=True)

    filename: str = Field(..., description="Name of the uploaded file.")
    scene_count: int = Field(..., description="Total number of scenes detected.")
    scenes: List[SceneContinuity] = Field(
        default_factory=list,
        description="Per-scene structured continuity data.",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Non-fatal errors encountered during processing.",
    )


class CallSheetResponse(BaseModel):
    """Response envelope for call sheet extraction & parsing."""

    model_config = ConfigDict(populate_by_name=True)

    filename: str = Field(..., description="Uploaded call sheet filename.")
    uploaded_path: str = Field(..., description="Path where file was saved.")
    extracted_path: str = Field(..., description="Path to plain text extracted file.")
    call_sheet: CallSheetData = Field(..., description="Parsed call sheet metadata object.")


class HealthResponse(BaseModel):
    """API health check response."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = Field("ok", description="Liveness status.")
    version: str = Field(..., description="API semantic version.")
    granite_configured: bool = Field(
        ...,
        description="True when local Granite LLM integration configuration is active.",
    )
