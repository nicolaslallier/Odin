"""Unit tests for data CRUD routes.

This module tests the data routes with mocked dependencies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.api.domain.entities import DataItem as DataItemEntity
from src.api.exceptions import DatabaseError, ResourceNotFoundError

if TYPE_CHECKING:
    from unittest.mock import Mock


@pytest_asyncio.fixture
async def client(mock_service_container: Mock):
    """Create an async test client for the API.

    Args:
        mock_service_container: Mocked service container from fixtures

    Yields:
        Async HTTP client for testing
    """
    from src.api.app import create_app

    # Mock the ServiceContainer to return our mock instead of initializing real services
    with patch("src.api.app.ServiceContainer", return_value=mock_service_container):
        # Mock table creation functions to avoid database operations
        with patch("src.api.repositories.data_repository.create_tables", new=AsyncMock()):
            with patch("src.api.repositories.image_repository.create_tables", new=AsyncMock()):
                # Mock logging configuration
                with patch("src.api.logging_config.configure_logging_with_db"):
                    app = create_app()

                    # Manually trigger lifespan startup event with mocked container
                    async with app.router.lifespan_context(app):
                        transport = ASGITransport(app=app)
                        async with AsyncClient(transport=transport, base_url="http://test") as ac:
                            yield ac


@pytest.mark.unit
class TestDataRoutes:
    """Test data CRUD routes."""

    @pytest.mark.asyncio
    async def test_create_data_item_success(self, client: AsyncClient) -> None:
        """Test successful data item creation."""
        from src.api.routes import data

        # Mock repository
        mock_repo = MagicMock()
        mock_entity = DataItemEntity(
            name="Test", description="Test description", data={"key": "value"}
        )
        mock_entity.id = 1
        mock_repo.create = AsyncMock(return_value=mock_entity)

        # Override dependency
        async def mock_get_repository():
            yield mock_repo

        app = client._transport.app
        app.dependency_overrides[data.get_repository] = mock_get_repository

        response = await client.post(
            "/data/",
            json={"name": "Test", "description": "Test description", "data": {"key": "value"}},
        )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data_response = response.json()
        assert data_response["id"] == 1
        assert data_response["name"] == "Test"
        assert data_response["description"] == "Test description"

    @pytest.mark.asyncio
    async def test_create_data_item_database_error(self, client: AsyncClient) -> None:
        """Test data item creation with database error."""
        from src.api.routes import data

        # Mock repository to raise DatabaseError
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(side_effect=DatabaseError("Database connection failed", {}))

        async def mock_get_repository():
            yield mock_repo

        app = client._transport.app
        app.dependency_overrides[data.get_repository] = mock_get_repository

        response = await client.post(
            "/data/", json={"name": "Test", "description": "Test description", "data": {}}
        )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_read_data_item_success(self, client: AsyncClient) -> None:
        """Test successful data item retrieval."""
        from src.api.routes import data

        # Mock repository
        mock_repo = MagicMock()
        mock_entity = DataItemEntity(
            name="Test", description="Test description", data={"key": "value"}
        )
        mock_entity.id = 1
        mock_repo.get_by_id = AsyncMock(return_value=mock_entity)

        async def mock_get_repository():
            yield mock_repo

        app = client._transport.app
        app.dependency_overrides[data.get_repository] = mock_get_repository

        response = await client.get("/data/1")

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data_response = response.json()
        assert data_response["id"] == 1
        assert data_response["name"] == "Test"

    @pytest.mark.asyncio
    async def test_read_data_item_not_found(self, client: AsyncClient) -> None:
        """Test reading nonexistent data item."""
        from src.api.routes import data

        # Mock repository to raise ResourceNotFoundError
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(
            side_effect=ResourceNotFoundError("Item not found", {"id": 999})
        )

        async def mock_get_repository():
            yield mock_repo

        app = client._transport.app
        app.dependency_overrides[data.get_repository] = mock_get_repository

        response = await client.get("/data/999")

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_data_item_success(self, client: AsyncClient) -> None:
        """Test successful data item update."""
        from src.api.routes import data

        # Mock repository
        mock_repo = MagicMock()
        mock_entity = DataItemEntity(name="Original", description="Original desc", data={})
        mock_entity.id = 1

        updated_entity = DataItemEntity(
            name="Updated", description="Updated desc", data={"new": "data"}
        )
        updated_entity.id = 1

        mock_repo.get_by_id = AsyncMock(return_value=mock_entity)
        mock_repo.update = AsyncMock(return_value=updated_entity)

        async def mock_get_repository():
            yield mock_repo

        app = client._transport.app
        app.dependency_overrides[data.get_repository] = mock_get_repository

        response = await client.put(
            "/data/1",
            json={"name": "Updated", "description": "Updated desc", "data": {"new": "data"}},
        )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data_response = response.json()
        assert data_response["id"] == 1
        assert data_response["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_update_data_item_not_found(self, client: AsyncClient) -> None:
        """Test updating nonexistent data item."""
        from src.api.routes import data

        # Mock repository to raise ResourceNotFoundError
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(
            side_effect=ResourceNotFoundError("Item not found", {"id": 999})
        )

        async def mock_get_repository():
            yield mock_repo

        app = client._transport.app
        app.dependency_overrides[data.get_repository] = mock_get_repository

        response = await client.put(
            "/data/999", json={"name": "Updated", "description": "Updated desc", "data": {}}
        )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_data_item_success(self, client: AsyncClient) -> None:
        """Test successful data item deletion."""
        from src.api.routes import data

        # Mock repository
        mock_repo = MagicMock()
        mock_repo.delete = AsyncMock(return_value=None)

        async def mock_get_repository():
            yield mock_repo

        app = client._transport.app
        app.dependency_overrides[data.get_repository] = mock_get_repository

        response = await client.delete("/data/1")

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data_response = response.json()
        assert "message" in data_response

    @pytest.mark.asyncio
    async def test_delete_data_item_not_found(self, client: AsyncClient) -> None:
        """Test deleting nonexistent data item."""
        from src.api.routes import data

        # Mock repository to raise ResourceNotFoundError
        mock_repo = MagicMock()
        mock_repo.delete = AsyncMock(
            side_effect=ResourceNotFoundError("Item not found", {"id": 999})
        )

        async def mock_get_repository():
            yield mock_repo

        app = client._transport.app
        app.dependency_overrides[data.get_repository] = mock_get_repository

        response = await client.delete("/data/999")

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_data_items_success(self, client: AsyncClient) -> None:
        """Test successful data items listing."""
        from src.api.routes import data

        # Mock repository
        mock_repo = MagicMock()
        mock_entity1 = DataItemEntity(name="Item1", description="Desc1", data={})
        mock_entity1.id = 1
        mock_entity2 = DataItemEntity(name="Item2", description="Desc2", data={})
        mock_entity2.id = 2

        mock_repo.get_all = AsyncMock(return_value=[mock_entity1, mock_entity2])
        mock_repo.count = AsyncMock(return_value=2)

        async def mock_get_repository():
            yield mock_repo

        app = client._transport.app
        app.dependency_overrides[data.get_repository] = mock_get_repository

        response = await client.get("/data/")

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data_response = response.json()
        assert data_response["total"] == 2
        assert len(data_response["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_data_items_empty(self, client: AsyncClient) -> None:
        """Test listing data items when none exist."""
        from src.api.routes import data

        # Mock repository with empty list
        mock_repo = MagicMock()
        mock_repo.get_all = AsyncMock(return_value=[])
        mock_repo.count = AsyncMock(return_value=0)

        async def mock_get_repository():
            yield mock_repo

        app = client._transport.app
        app.dependency_overrides[data.get_repository] = mock_get_repository

        response = await client.get("/data/")

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data_response = response.json()
        assert data_response["total"] == 0
        assert len(data_response["items"]) == 0
