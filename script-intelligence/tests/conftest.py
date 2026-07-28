"""
VERSE Test Suite - Fixtures and Shared Configuration.
"""

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def sample_screenplay_text() -> str:
    return """\
INT. SARAH'S APARTMENT - KITCHEN - NIGHT

Sarah (30s, wearing a blue jacket) stands at the kitchen counter.
She holds a hot mug of coffee in her right hand.

SARAH
I can't believe this is happening.

John enters through the back door, carrying a silver briefcase.

EXT. ALLEYWAY - NIGHT

John runs down the rain-slicked alleyway. Sarah follows closely behind.
"""


@pytest.fixture
def sample_call_sheet_text() -> str:
    return """\
PRODUCTION: VERSE Season 1
DATE: 2026-07-28
DIRECTOR: Jane Doe
LOCATION: Studio 4 - Main Stage
CALL TIME: 07:00 AM

SCHEDULE:
1 | INT. KITCHEN - NIGHT
2A | EXT. ALLEYWAY - NIGHT

CAST
SARAH - Lead Actress
JOHN - Lead Actor

CREW
Director of Photography
Script Supervisor
"""
