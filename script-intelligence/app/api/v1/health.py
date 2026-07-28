"""
VERSE API v1 - Health Check Endpoint.
"""

from fastapi import APIRouter
from app.core.config import settings
from app.llm.granite_client import is_granite_configured
from app.schemas.responses import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="API health check",
    description="Returns API status, semantic version string, and Granite/Ollama configuration status.",
)
def health_check() -> HealthResponse:
    """Liveness probe endpoint."""
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        granite_configured=is_granite_configured(),
    )
