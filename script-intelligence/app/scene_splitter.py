"""
VERSE – Continuity Script Intelligence
app/scene_splitter.py (Backwards Compatibility Layer)

Re-exports scene splitting logic from app.parsers.scene_splitter.
"""

from app.parsers.scene_splitter import split_into_scenes

__all__ = ["split_into_scenes"]