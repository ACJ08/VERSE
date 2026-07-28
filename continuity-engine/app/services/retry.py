"""
Retry utilities for VERSE Continuity Engine.
Handles temporary Granite/Ollama/API failures.
"""

from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)


def retry_with_backoff(
    retries: int = 3,
    base_delay: float = 1.0,
    exceptions=(Exception,),
):
    """
    Exponential backoff retry decorator.

    Example:
        @retry_with_backoff(retries=3)
        def call_granite():
            ...
    """

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            last_error = None

            for attempt in range(retries):

                try:
                    return func(*args, **kwargs)

                except exceptions as exc:
                    last_error = exc

                    wait = base_delay * (2 ** attempt)

                    logger.warning(
                        "Retry %s/%s failed for %s. Retrying in %.1fs",
                        attempt + 1,
                        retries,
                        func.__name__,
                        wait,
                    )

                    time.sleep(wait)

            raise last_error

        return wrapper

    return decorator