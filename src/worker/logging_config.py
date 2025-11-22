"""Structured logging configuration for the Worker service.

This module configures structured logging for Celery workers with
JSON output for better log aggregation.
"""

from __future__ import annotations

import logging
from typing import Any

# Import the structured logging from API (DRY principle)
from src.api.logging_config import StructuredFormatter, LoggerAdapter, get_logger as api_get_logger


def configure_worker_logging(
    level: str = "INFO",
    use_json: bool = True,
) -> None:
    """Configure structured logging for Celery workers.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting
    """
    # Import here to avoid circular dependencies
    from src.api.logging_config import configure_logging

    # Use the shared logging configuration
    configure_logging(level=level, use_json=use_json)

    # Additional Celery-specific configuration
    celery_logger = logging.getLogger("celery")
    celery_logger.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_task_logger(name: str, task_id: str | None = None, **context: Any) -> logging.Logger | LoggerAdapter:
    """Get a logger for Celery tasks with task context.

    Args:
        name: Logger name (usually __name__)
        task_id: Celery task ID
        **context: Additional context to add to all logs

    Returns:
        Logger or LoggerAdapter with context

    Example:
        >>> logger = get_task_logger(__name__, task_id=self.request.id)
        >>> logger.info("Processing task")
    """
    if task_id:
        context["task_id"] = task_id
    return api_get_logger(name, **context)

