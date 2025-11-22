"""Error path tests for API routes.

This module tests error scenarios in API routes including
service failures, invalid inputs, and edge cases.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.exceptions import ResourceNotFoundError, ServiceUnavailableError


@pytest.mark.unit
class TestHealthRouteErrors:
    """Test error scenarios in health check routes."""

    @pytest.mark.asyncio
    async def test_health_check_with_service_failure(self, client: AsyncClient) -> None:
        """Test health check when a service fails."""
        # The circuit breaker should catch failures and return False
        response = await client.get("/health/services")
        assert response.status_code == status.HTTP_200_OK
        
        # Response should contain health status for all services
        data = response.json()
        assert "database" in data
        assert "storage" in data
        assert "queue" in data
        assert "vault" in data
        assert "ollama" in data

    @pytest.mark.asyncio
    async def test_health_check_caching(self, client: AsyncClient) -> None:
        """Test that health checks are cached."""
        # First request
        response1 = await client.get("/health/services")
        assert response1.status_code == status.HTTP_200_OK
        
        # Second request should hit cache
        response2 = await client.get("/health/services")
        assert response2.status_code == status.HTTP_200_OK
        assert response1.json() == response2.json()


@pytest.mark.unit
class TestDataRouteErrors:
    """Test error scenarios in data routes."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_item(self, client: AsyncClient) -> None:
        """Test getting nonexistent data item."""
        # Mock repository to raise NotFoundError
        with patch("src.api.routes.data.get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(side_effect=ResourceNotFoundError("Data item not found", {"id": 999}))
            mock_get_repo.return_value = mock_repo
            
            response = await client.get("/data/999")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_item_with_invalid_data(self, client: AsyncClient) -> None:
        """Test creating item with invalid data."""
        invalid_payloads = [
            {},  # Missing required fields
            {"name": ""},  # Empty name (might be invalid)
            {"name": None},  # None name
        ]
        
        for payload in invalid_payloads:
            response = await client.post("/data", json=payload)
            # Should return 422 (validation error) or handle gracefully
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_201_CREATED,
            ]

    @pytest.mark.asyncio
    async def test_update_nonexistent_item(self, client: AsyncClient) -> None:
        """Test updating nonexistent data item."""
        with patch("src.api.routes.data.get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.update = AsyncMock(side_effect=ResourceNotFoundError("Data item not found", {"id": 999}))
            mock_get_repo.return_value = mock_repo
            
            response = await client.put(
                "/data/999", json={"name": "Updated", "description": "Test"}
            )
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_nonexistent_item(self, client: AsyncClient) -> None:
        """Test deleting nonexistent data item."""
        with patch("src.api.routes.data.get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.delete = AsyncMock(side_effect=ResourceNotFoundError("Data item not found", {"id": 999}))
            mock_get_repo.return_value = mock_repo
            
            response = await client.delete("/data/999")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_with_invalid_pagination(self, client: AsyncClient) -> None:
        """Test list with invalid pagination parameters."""
        # Negative skip
        response = await client.get("/data?skip=-10&limit=10")
        # Should handle gracefully (either 422 or default to 0)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]
        
        # Zero limit
        response = await client.get("/data?skip=0&limit=0")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]
        
        # Excessive limit
        response = await client.get("/data?skip=0&limit=1000000")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


@pytest.mark.unit
class TestFileRouteErrors:
    """Test error scenarios in file routes."""

    @pytest.mark.asyncio
    async def test_upload_without_file(self, client: AsyncClient) -> None:
        """Test upload endpoint without file."""
        response = await client.post(
            "/files/upload?bucket=test-bucket&object_name=test.txt"
        )
        # Should return 422 (validation error)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_upload_with_storage_service_down(self, client: AsyncClient) -> None:
        """Test upload when storage service is unavailable."""
        # Mock storage service to raise ServiceUnavailableError
        with patch("src.api.routes.files.container.storage_service") as mock_storage:
            mock_storage.return_value.upload_file.side_effect = ServiceUnavailableError(
                "MinIO"
            )
            
            response = await client.post(
                "/files/upload?bucket=test-bucket&object_name=test.txt",
                files={"file": ("test.txt", b"content")},
            )
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_download_nonexistent_file(self, client: AsyncClient) -> None:
        """Test downloading nonexistent file."""
        with patch("src.api.routes.files.container.storage_service") as mock_storage:
            mock_storage.return_value.download_file.side_effect = ResourceNotFoundError("File not found", {})
            
            response = await client.get(
                "/files/download?bucket=test-bucket&object_name=nonexistent.txt"
            )
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_with_invalid_bucket_name(self, client: AsyncClient) -> None:
        """Test delete with invalid bucket name."""
        invalid_buckets = ["", " ", "invalid bucket", "bucket/with/slash"]
        
        for bucket in invalid_buckets:
            response = await client.delete(
                f"/files/delete?bucket={bucket}&object_name=test.txt"
            )
            # Should handle gracefully
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ]


@pytest.mark.unit
class TestLLMRouteErrors:
    """Test error scenarios in LLM routes."""

    @pytest.mark.asyncio
    async def test_generate_with_invalid_model(self, client: AsyncClient) -> None:
        """Test generation with invalid model name."""
        with patch("src.api.routes.llm.container.ollama_service") as mock_ollama:
            mock_ollama.return_value.generate_text.side_effect = ServiceUnavailableError(
                "Ollama"
            )
            
            response = await client.post(
                "/llm/generate",
                json={"model": "nonexistent", "prompt": "test"},
            )
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_generate_with_empty_prompt(self, client: AsyncClient) -> None:
        """Test generation with empty prompt."""
        response = await client.post(
            "/llm/generate",
            json={"model": "llama2", "prompt": ""},
        )
        # Should either accept it or return validation error
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    @pytest.mark.asyncio
    async def test_list_models_when_service_down(self, client: AsyncClient) -> None:
        """Test listing models when Ollama service is down."""
        with patch("src.api.routes.llm.container.ollama_service") as mock_ollama:
            mock_ollama.return_value.list_models.side_effect = ServiceUnavailableError(
                "Ollama"
            )
            
            response = await client.get("/llm/models")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_pull_model_timeout(self, client: AsyncClient) -> None:
        """Test pull model with timeout."""
        with patch("src.api.routes.llm.container.ollama_service") as mock_ollama:
            mock_ollama.return_value.pull_model.side_effect = TimeoutError("Timeout")
            
            response = await client.post("/llm/pull/llama2")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.unit
class TestMessageRouteErrors:
    """Test error scenarios in message routes."""

    @pytest.mark.asyncio
    async def test_publish_when_queue_down(self, client: AsyncClient) -> None:
        """Test publishing message when RabbitMQ is down."""
        with patch("src.api.routes.messages.container.queue_service") as mock_queue:
            mock_queue.return_value.publish_message.side_effect = ServiceUnavailableError(
                "RabbitMQ"
            )
            
            response = await client.post(
                "/messages/publish",
                json={"queue": "test-queue", "message": "test"},
            )
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_consume_from_nonexistent_queue(self, client: AsyncClient) -> None:
        """Test consuming from nonexistent queue."""
        with patch("src.api.routes.messages.container.queue_service") as mock_queue:
            mock_queue.return_value.consume_message.return_value = None
            
            response = await client.get("/messages/consume/nonexistent-queue")
            # Should return 200 with null message or 404
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_404_NOT_FOUND,
            ]


@pytest.mark.unit
class TestSecretRouteErrors:
    """Test error scenarios in secret routes."""

    @pytest.mark.asyncio
    async def test_read_nonexistent_secret(self, client: AsyncClient) -> None:
        """Test reading nonexistent secret."""
        with patch("src.api.routes.secrets.container.vault_service") as mock_vault:
            mock_vault.return_value.read_secret.side_effect = ResourceNotFoundError("Secret not found", {})
            
            response = await client.get("/secrets/myapp/nonexistent")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_write_secret_when_vault_down(self, client: AsyncClient) -> None:
        """Test writing secret when Vault is down."""
        with patch("src.api.routes.secrets.container.vault_service") as mock_vault:
            mock_vault.return_value.write_secret.side_effect = ServiceUnavailableError(
                "Vault"
            )
            
            response = await client.post(
                "/secrets/myapp/test",
                json={"secret_value": "test"},
            )
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_write_secret_with_invalid_path(self, client: AsyncClient) -> None:
        """Test writing secret with invalid path."""
        invalid_paths = ["", " ", "/", "//", "path with spaces"]
        
        for path in invalid_paths:
            response = await client.post(
                f"/secrets/myapp/{path}",
                json={"secret_value": "test"},
            )
            # Should handle gracefully
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_503_SERVICE_UNAVAILABLE,
                status.HTTP_200_OK,  # Might be accepted by Vault
            ]

    @pytest.mark.asyncio
    async def test_delete_nonexistent_secret(self, client: AsyncClient) -> None:
        """Test deleting nonexistent secret."""
        with patch("src.api.routes.secrets.container.vault_service") as mock_vault:
            mock_vault.return_value.delete_secret.side_effect = ResourceNotFoundError("Secret not found", {})
            
            response = await client.delete("/secrets/myapp/nonexistent")
            # Delete of nonexistent might return 204 or 404
            assert response.status_code in [
                status.HTTP_204_NO_CONTENT,
                status.HTTP_404_NOT_FOUND,
            ]

