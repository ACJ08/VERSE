"""
VERSE – Continuity Script Intelligence
app/granite.py (Backwards Compatibility Layer)

Re-exports GraniteClient and convenience functions from app.llm.granite_client.
"""

from app.llm.granite_client import (
    GraniteClient,
    analyse_scene,
    is_granite_configured,
)

__all__ = [
    "GraniteClient",
    "analyse_scene",
    "is_granite_configured",
]