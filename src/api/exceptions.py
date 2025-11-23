"""Custom exceptions for the API service.

This module defines domain-specific exceptions that provide better error
handling and context than generic exceptions.
"""

from __future__ import annotations

from typing import Any


class OdinAPIError(Exception):
    """Base exception for all Odin API errors.

    This is the base class for all custom exceptions in the API service,
    following the Single Responsibility Principle by providing a clear
    exception hierarchy.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ServiceUnavailableError(OdinAPIError):
    """Raised when an external service is unavailable.

    Examples:
        - Database connection failed
        - Message queue unreachable
        - Storage service down
    """

    pass


class ResourceNotFoundError(OdinAPIError):
    """Raised when a requested resource does not exist.

    Examples:
        - File not found in storage
        - Secret not found in vault
        - Data item not found in database
    """

    pass


class ValidationError(OdinAPIError):
    """Raised when input validation fails.

    Examples:
        - Invalid file format
        - Missing required fields
        - Data out of acceptable range
    """

    pass


class StorageError(OdinAPIError):
    """Raised when storage operations fail.

    Examples:
        - Failed to upload file
        - Failed to delete object
        - Bucket creation failed
    """

    pass


class QueueError(OdinAPIError):
    """Raised when queue operations fail.

    Examples:
        - Failed to publish message
        - Failed to consume message
        - Queue declaration failed
    """

    pass


class VaultError(OdinAPIError):
    """Raised when Vault operations fail.

    Examples:
        - Failed to write secret
        - Failed to read secret
        - Authentication failed
    """

    pass


class DatabaseError(OdinAPIError):
    """Raised when database operations fail.

    Examples:
        - Connection failed
        - Query execution failed
        - Transaction rollback
    """

    pass


class LLMError(OdinAPIError):
    """Raised when LLM operations fail.

    Examples:
        - Model not available
        - Generation timeout
        - Invalid model configuration
    """

    pass


class ConfluenceError(OdinAPIError):
    """Raised when Confluence operations fail.

    Examples:
        - Failed to retrieve page
        - Failed to create/update page
        - Authentication failed
        - Space not accessible
    """

    pass
