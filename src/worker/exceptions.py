"""Custom exceptions for the Worker service.

This module defines domain-specific exceptions for Celery worker tasks.
"""

from __future__ import annotations

from typing import Any, Optional


class WorkerError(Exception):
    """Base exception for all worker errors.

    This is the base class for all custom exceptions in the worker service.
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class BatchProcessingError(WorkerError):
    """Raised when batch processing fails.

    Examples:
        - Batch size too large
        - Invalid batch data
        - Batch processing timeout
    """

    pass


class TaskConfigurationError(WorkerError):
    """Raised when task configuration is invalid.

    Examples:
        - Missing required configuration
        - Invalid configuration values
        - Configuration validation failed
    """

    pass


class ExternalServiceError(WorkerError):
    """Raised when external service calls fail.

    Examples:
        - Database connection failed
        - HTTP request timeout
        - Service unavailable
    """

    pass

