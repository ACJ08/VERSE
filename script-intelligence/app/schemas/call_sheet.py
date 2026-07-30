"""
VERSE Schemas - Production Call Sheet Models.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class CallSheetData(BaseModel):
    """Structured call sheet production metadata."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field("", description="Production shoot date.")
    production: str = Field("", description="Production / film project name.")
    director: str = Field("", description="Director name.")
    location: str = Field("", description="Filming location / studio details.")
    scenes: List[str] = Field(default_factory=list, description="Scheduled scene numbers.")
    cast: List[str] = Field(default_factory=list, description="Cast list & call times.")
    crew: List[str] = Field(default_factory=list, description="Crew members & departments.")
    shooting_time: str = Field("", description="General crew call time / shoot start time.")
