"""HTTP surface. Import `router` and mount it in the shared FastAPI app."""

from app.api.routes import router

__all__ = ["router"]
