"""Unit tests for API exceptions.

This module tests custom exception classes used in the API.
"""

from __future__ import annotations

import pytest

from src.api.exceptions import (
    DatabaseError,
    LLMError,
    OdinAPIError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    StorageError,
    VaultError,
)


@pytest.mark.unit
class TestOdinAPIError:
    """Test base OdinAPIError exception."""

    def test_basic_error(self) -> None:
        """Test basic error creation."""
        error = OdinAPIError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}

    def test_error_with_details(self) -> None:
        """Test error with details."""
        details = {"code": 123, "field": "test"}
        error = OdinAPIError("Test error", details)
        assert error.message == "Test error"
        assert error.details == details

    def test_error_repr(self) -> None:
        """Test error representation."""
        error = OdinAPIError("Test error", {"key": "value"})
        repr_str = repr(error)
        assert "Test error" in repr_str


@pytest.mark.unit
class TestDatabaseError:
    """Test DatabaseError exception."""

    def test_database_error(self) -> None:
        """Test database error creation."""
        error = DatabaseError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, OdinAPIError)

    def test_database_error_with_details(self) -> None:
        """Test database error with details."""
        details = {"host": "localhost", "port": 5432}
        error = DatabaseError("Connection failed", details)
        assert error.details == details


@pytest.mark.unit
class TestResourceNotFoundError:
    """Test ResourceNotFoundError exception."""

    def test_resource_not_found(self) -> None:
        """Test resource not found error."""
        error = ResourceNotFoundError("Item not found")
        assert str(error) == "Item not found"
        assert isinstance(error, OdinAPIError)

    def test_resource_not_found_with_id(self) -> None:
        """Test resource not found with ID."""
        error = ResourceNotFoundError("Item not found", {"id": 123})
        assert error.details["id"] == 123


@pytest.mark.unit
class TestServiceUnavailableError:
    """Test ServiceUnavailableError exception."""

    def test_service_unavailable(self) -> None:
        """Test service unavailable error."""
        error = ServiceUnavailableError("Service down")
        assert str(error) == "Service down"
        assert isinstance(error, OdinAPIError)

    def test_service_unavailable_with_service_name(self) -> None:
        """Test service unavailable with service name."""
        error = ServiceUnavailableError("Service down", {"service": "database"})
        assert error.details["service"] == "database"


@pytest.mark.unit
class TestStorageError:
    """Test StorageError exception."""

    def test_storage_error(self) -> None:
        """Test storage error creation."""
        error = StorageError("Upload failed")
        assert str(error) == "Upload failed"
        assert isinstance(error, OdinAPIError)

    def test_storage_error_with_bucket(self) -> None:
        """Test storage error with bucket info."""
        error = StorageError("Upload failed", {"bucket": "test-bucket"})
        assert error.details["bucket"] == "test-bucket"


@pytest.mark.unit
class TestVaultError:
    """Test VaultError exception."""

    def test_vault_error(self) -> None:
        """Test vault error creation."""
        error = VaultError("Secret not found")
        assert str(error) == "Secret not found"
        assert isinstance(error, OdinAPIError)

    def test_vault_error_with_path(self) -> None:
        """Test vault error with path."""
        error = VaultError("Secret not found", {"path": "myapp/secret"})
        assert error.details["path"] == "myapp/secret"


@pytest.mark.unit
class TestLLMError:
    """Test LLMError exception."""

    def test_llm_error(self) -> None:
        """Test LLM error creation."""
        error = LLMError("Model not found")
        assert str(error) == "Model not found"
        assert isinstance(error, OdinAPIError)

    def test_llm_error_with_model(self) -> None:
        """Test LLM error with model info."""
        error = LLMError("Generation failed", {"model": "llama2"})
        assert error.details["model"] == "llama2"
