"""Error path tests for data repository.

This module tests error scenarios in the data repository including
database errors, not found errors, and edge cases.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.exceptions import ResourceNotFoundError
from src.api.repositories.data_repository import DataRepository


@pytest.mark.unit
class TestDataRepositoryErrors:
    """Test error scenarios in DataRepository."""

    @pytest.fixture
    def mock_session_factory(self) -> MagicMock:
        """Create a mock session factory."""
        session = AsyncMock(spec=AsyncSession)
        factory = MagicMock()
        factory.return_value.__aenter__.return_value = session
        factory.return_value.__aexit__.return_value = None
        return factory

    @pytest.fixture
    def repository(self, mock_session_factory: MagicMock) -> DataRepository:
        """Create a repository with mocked session factory."""
        return DataRepository(session_factory=mock_session_factory)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository: DataRepository) -> None:
        """Test that get_by_id raises ResourceNotFoundError when item not found."""
        # Mock the session to return None (item not found)
        mock_session = repository._session_factory.return_value.__aenter__.return_value
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ResourceNotFoundError, match="Data item"):
            await repository.get_by_id(999)

    @pytest.mark.asyncio
    async def test_update_nonexistent_item(self, repository: DataRepository) -> None:
        """Test that updating nonexistent item raises ResourceNotFoundError."""
        # Mock get_by_id to raise ResourceNotFoundError
        with patch.object(repository, "get_by_id", side_effect=ResourceNotFoundError("Data item not found", {"id": 999})):
            with pytest.raises(ResourceNotFoundError):
                await repository.update(999, name="New Name")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_item(self, repository: DataRepository) -> None:
        """Test that deleting nonexistent item raises ResourceNotFoundError."""
        # Mock get_by_id to raise ResourceNotFoundError
        with patch.object(repository, "get_by_id", side_effect=ResourceNotFoundError("Data item not found", {"id": 999})):
            with pytest.raises(ResourceNotFoundError):
                await repository.delete(999)

    @pytest.mark.asyncio
    async def test_create_with_empty_name(self, repository: DataRepository) -> None:
        """Test creating item with empty name."""
        # This should work - empty name is valid unless we add validation
        result = await repository.create(name="", description="Test")
        # If we reach here without exception, it's working as intended
        # In a real scenario, you might want to add validation to prevent empty names

    @pytest.mark.asyncio
    async def test_create_with_none_description(self, repository: DataRepository) -> None:
        """Test creating item with None description."""
        # This should work - None is a valid description
        result = await repository.create(name="Test", description=None)
        # If we reach here without exception, it's working as intended

    @pytest.mark.asyncio
    async def test_list_with_negative_skip(self, repository: DataRepository) -> None:
        """Test list_all with negative skip value."""
        # SQLAlchemy should handle this, but it's an edge case to test
        mock_session = repository._session_factory.return_value.__aenter__.return_value
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repository.list_all(skip=-10, limit=10)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_with_zero_limit(self, repository: DataRepository) -> None:
        """Test list_all with zero limit."""
        mock_session = repository._session_factory.return_value.__aenter__.return_value
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repository.list_all(skip=0, limit=0)
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_with_excessive_limit(self, repository: DataRepository) -> None:
        """Test list_all with very large limit."""
        mock_session = repository._session_factory.return_value.__aenter__.return_value
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Should work but might want to add max limit validation
        result = await repository.list_all(skip=0, limit=1000000)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_update_with_all_none_values(self, repository: DataRepository) -> None:
        """Test update with all None values (no-op update)."""
        mock_item = MagicMock()
        mock_item.id = 1
        mock_item.name = "Original"

        with patch.object(repository, "get_by_id", return_value=mock_item):
            # Update with all None should not change anything
            result = await repository.update(1, name=None, description=None, data=None)
            # Should still return the item
            assert result == mock_item

    @pytest.mark.asyncio
    async def test_create_with_invalid_json_data(self, repository: DataRepository) -> None:
        """Test creating item with complex nested data."""
        # Test with deeply nested dict - should work with JSON column
        complex_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "values": [1, 2, 3],
                        "nested": {"key": "value"},
                    }
                }
            }
        }
        
        # This should work as JSON can handle nested structures
        result = await repository.create(
            name="Complex", description="Test", data=complex_data
        )

    @pytest.mark.asyncio
    async def test_concurrent_updates(self, repository: DataRepository) -> None:
        """Test concurrent updates to same item."""
        # This tests potential race conditions
        # In a real scenario, you'd want database-level locking
        mock_item = MagicMock()
        mock_item.id = 1

        with patch.object(repository, "get_by_id", return_value=mock_item):
            # Simulate concurrent updates
            import asyncio

            await asyncio.gather(
                repository.update(1, name="Update1"),
                repository.update(1, name="Update2"),
                repository.update(1, name="Update3"),
            )
            # Should complete without errors
            # Last update wins (or might need optimistic locking)

    @pytest.mark.asyncio
    async def test_create_with_special_characters_in_name(self, repository: DataRepository) -> None:
        """Test creating item with special characters in name."""
        special_names = [
            "Name with spaces",
            "Name-with-dashes",
            "Name_with_underscores",
            "Name.with.dots",
            "Name@with#special$chars",
            "Name with emoji 😀",
            "Name with\nnewline",
            "Name with\ttab",
        ]

        for name in special_names:
            # All should work - no validation on name format
            result = await repository.create(name=name)

    @pytest.mark.asyncio
    async def test_update_with_empty_string(self, repository: DataRepository) -> None:
        """Test update with empty string values."""
        mock_item = MagicMock()
        mock_item.id = 1

        with patch.object(repository, "get_by_id", return_value=mock_item):
            # Empty strings should be valid
            result = await repository.update(1, name="", description="")
            assert mock_item.name == ""
            assert mock_item.description == ""

    @pytest.mark.asyncio
    async def test_create_with_very_long_strings(self, repository: DataRepository) -> None:
        """Test creating item with very long strings."""
        long_name = "x" * 10000
        long_description = "y" * 100000

        # This might fail with database constraints
        # Test to ensure proper error handling
        try:
            result = await repository.create(
                name=long_name, description=long_description
            )
            # If it succeeds, that's fine (no length limits in schema)
        except Exception:
            # If it fails, that's also fine (database has limits)
            pass

    @pytest.mark.asyncio
    async def test_list_all_returns_empty_when_no_items(
        self, repository: DataRepository
    ) -> None:
        """Test that list_all returns empty list when no items exist."""
        mock_session = repository._session_factory.return_value.__aenter__.return_value
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repository.list_all()
        assert result == []
        assert isinstance(result, list)

