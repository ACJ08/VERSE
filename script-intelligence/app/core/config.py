"""
VERSE Core - Centralized Configuration Management.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Ensure .env file is loaded if present
load_dotenv()


class Settings:
    """Application settings loaded from environment variables with safe defaults."""

    # Project Information
    PROJECT_NAME: str = "ContinuityAI Script Intelligence API"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"

    # LLM / Granite / Ollama Configuration
    # Default port is 11435 (llama-cpp-python server) to avoid conflict with the
    # continuity-engine which runs on port 8000.
    GRANITE_BASE_URL: str = os.getenv("GRANITE_BASE_URL", "http://localhost:11435/v1").rstrip("/")
    GRANITE_MODEL: str = os.getenv("GRANITE_MODEL", "granite-3.3-2b-instruct")
    GRANITE_API_KEY: str = os.getenv("GRANITE_API_KEY", "EMPTY")
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "120.0"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "2"))
    MAX_PARALLEL_SCENE_ANALYSES: int = int(os.getenv("MAX_PARALLEL_SCENE_ANALYSES", "4"))

    # Continuity engine integration
    CONTINUITY_ENGINE_URL: str = os.getenv("CONTINUITY_ENGINE_URL", "http://localhost:8000").rstrip("/")
    CONTINUITY_ENGINE_TOKEN: str = os.getenv("CONTINUITY_ENGINE_TOKEN", "")

    # File Upload & Directory Configuration
    SCRIPT_UPLOAD_DIR: str = os.getenv("SCRIPT_UPLOAD_DIR", "uploads/scripts")
    CALL_SHEET_UPLOAD_DIR: str = os.getenv("CALL_SHEET_UPLOAD_DIR", "uploads/call_sheets")
    SCRIPT_EXTRACT_DIR: str = os.getenv("SCRIPT_EXTRACT_DIR", "extracted/scripts")
    CALL_SHEET_EXTRACT_DIR: str = os.getenv("CALL_SHEET_EXTRACT_DIR", "extracted/call_sheets")
    
    # Security Configuration
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx", ".txt"}
    ALLOWED_MIME_TYPES: set[str] = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "application/octet-stream",  # Allow generic octet stream if extension passes validation
    }

    @property
    def is_granite_configured(self) -> bool:
        """Check if local Granite inference server settings are populated."""
        return bool(self.GRANITE_BASE_URL) and bool(self.GRANITE_MODEL)


settings = Settings()
