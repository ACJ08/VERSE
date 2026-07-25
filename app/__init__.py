"""
VERSE – Continuity Script Intelligence
app/__init__.py

Package initializer.

Exposes only the version string at package import time.  The FastAPI
``app`` instance is intentionally NOT re-exported here to avoid a
circular import chain:

    __init__.py → main.py → api.py → __init__.py (circular)

Import ``app.main.app`` directly when you need the FastAPI instance
(e.g. in uvicorn or test fixtures).
"""

from app._version import __version__  # noqa: F401

__all__ = ["__version__"]
