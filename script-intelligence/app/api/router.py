"""
VERSE API Router Module - Exports top-level APIRouter for inclusion in main FastAPI app.
"""

from fastapi import APIRouter
from app.api.v1 import v1_router

router = APIRouter()
router.include_router(v1_router)

__all__ = ["router"]
