"""
VERSE Core - Standardized Exception Hierarchy.
"""

from typing import Optional, Any


class VERSEError(Exception):
    """Base exception for all VERSE application domain errors."""

    def __init__(self, message: str, status_code: int = 500, details: Optional[Any] = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class ParsingError(VERSEError):
    """Raised when document extraction or scene parsing fails."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=422, details=details)


class InferenceError(VERSEError):
    """Raised when the LLM connection or extraction fails."""

    def __init__(self, message: str, details: Optional[Any] = None, status_code: int = 503) -> None:
        super().__init__(message, status_code=status_code, details=details)


class ValidationError(VERSEError):
    """Raised when request payload or data schema validation fails."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=400, details=details)


class SecurityError(VERSEError):
    """Raised when security checks (path traversal, file size limit) fail."""

    def __init__(self, message: str, status_code: int = 400, details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=status_code, details=details)
