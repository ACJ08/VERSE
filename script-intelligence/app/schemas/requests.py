"""
VERSE Schemas - API Request Envelope Models.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


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
