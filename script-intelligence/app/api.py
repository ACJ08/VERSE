"""
VERSE – Continuity Script Intelligence
app/api.py (Backwards Compatibility Module)

Exports the main router from app.api.router.
"""

from app.api.router import router

__all__ = ["router"]