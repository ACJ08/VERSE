"""
VERSE Core - Structured Logging & Performance Monitoring.
"""

import logging
import sys
import time
from contextlib import contextmanager
from typing import Generator


def setup_logging(level: int = logging.INFO) -> None:
    """Configure system-wide structured logging format."""
    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance."""
    return logging.getLogger(name)


@contextmanager
def timed_execution(action_name: str, logger: logging.Logger) -> Generator[None, None, None]:
    """Context manager to measure and log execution duration for operations."""
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start_time
        logger.info("%s completed in %.3f seconds", action_name, elapsed)
