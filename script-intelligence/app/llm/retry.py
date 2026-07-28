"""
VERSE LLM - Exponential Backoff & Retry Logic.
"""

import time
import functools
from typing import Callable, TypeVar, Any

from app.core.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T")


def retry_with_backoff(
    retries: int = 3,
    backoff_factor: float = 1.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator for retrying a function with exponential backoff on specified exceptions.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempts = 0
            func_name = getattr(func, "__name__", str(func))
            while attempts < retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    attempts += 1
                    if attempts >= retries:
                        logger.error("Function '%s' failed after %d retries. Exception: %s", func_name, retries, exc)
                        raise
                    sleep_time = backoff_factor * (2 ** (attempts - 1))
                    logger.warning("Retrying '%s' (attempt %d/%d) in %.2fs due to: %s", func_name, attempts, retries, sleep_time, exc)
                    time.sleep(sleep_time)
            return func(*args, **kwargs)
        return wrapper
    return decorator
