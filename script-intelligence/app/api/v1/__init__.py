"""
VERSE API v1 Router Aggregator.
"""

from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.scripts import router as scripts_router
from app.api.v1.scenes import router as scenes_router
from app.api.v1.call_sheets import router as call_sheets_router

v1_router = APIRouter()
v1_router.include_router(health_router)
v1_router.include_router(scripts_router)
v1_router.include_router(scenes_router)
v1_router.include_router(call_sheets_router)

__all__ = ["v1_router"]
