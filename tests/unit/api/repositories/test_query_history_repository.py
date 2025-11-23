"""Unit tests for query history repository.

This module tests the QueryHistoryRepository class which manages
the persistence of SQL query execution history.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.api.exceptions import DatabaseError, ResourceNotFoundError
from src.api.repositories.query_history_repository import QueryHistory, QueryHistoryRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock database session.

    Returns:
        AsyncMock instance for database session
    """
    return AsyncMock()


@pytest.fixture
def query_history_repo(mock_session: AsyncMock) -> QueryHistoryRepository:
    """Create a QueryHistoryRepository instance with mocked session.

    Args:
        mock_session: Mock database session

    Returns:
        QueryHistoryRepository instance for testing
    """
    return QueryHistoryRepository(mock_session)


@pytest.fixture
def sample_query_history() -> QueryHistory:
    """Create a sample query history entity.

    Returns:
        QueryHistory instance for testing
    """
    return QueryHistory(
        id=None,
        query_text="SELECT * FROM users",
        executed_at=datetime(2025, 1, 1, 12, 0, 0),
        execution_time_ms=150.5,
        status="success",
        row_count=10,
        error_message=None,
    )


class TestCreate:
    """Tests for create method."""

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        query_history_repo: QueryHistoryRepository,
        mock_session: AsyncMock,
        sample_query_history: QueryHistory,
    ) -> None:
        """Test successful creation of query history record."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 1
        mock_session.execute.return_value = mock_result

        # Act
        result = await query_history_repo.create(sample_query_history)

        # Assert
        assert result.id == 1
        assert result.query_text == "SELECT * FROM users"
        assert result.status == "success"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_database_error(
        self,
        query_history_repo: QueryHistoryRepository,
        mock_session: AsyncMock,
        sample_query_history: QueryHistory,
    ) -> None:
        """Test handling of database errors during creation."""
        # Arrange
        mock_session.execute.side_effect = SQLAlchemyError("Connection failed")

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to create query history"):
            await query_history_repo.create(sample_query_history)

        mock_session.rollback.assert_called_once()


class TestGetById:
    """Tests for get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test successful retrieval of query history by ID."""
        # Arrange
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.query_text = "SELECT * FROM users"
        mock_row.executed_at = datetime(2025, 1, 1, 12, 0, 0)
        mock_row.execution_time_ms = 150.5
        mock_row.status = "success"
        mock_row.row_count = 10
        mock_row.error_message = None
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        # Act
        result = await query_history_repo.get_by_id(1)

        # Assert
        assert result.id == 1
        assert result.query_text == "SELECT * FROM users"
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test retrieval when query history not found."""
        # Arrange
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ResourceNotFoundError, match="Query history not found"):
            await query_history_repo.get_by_id(999)

    @pytest.mark.asyncio
    async def test_get_by_id_database_error(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test handling of database errors during retrieval."""
        # Arrange
        mock_session.execute.side_effect = SQLAlchemyError("Connection timeout")

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to retrieve query history"):
            await query_history_repo.get_by_id(1)


class TestGetRecent:
    """Tests for get_recent method."""

    @pytest.mark.asyncio
    async def test_get_recent_success(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test successful retrieval of recent query history."""
        # Arrange
        mock_result = MagicMock()
        mock_rows = [
            MagicMock(
                id=2,
                query_text="SELECT * FROM posts",
                executed_at=datetime(2025, 1, 1, 12, 5, 0),
                execution_time_ms=200.0,
                status="success",
                row_count=20,
                error_message=None,
            ),
            MagicMock(
                id=1,
                query_text="SELECT * FROM users",
                executed_at=datetime(2025, 1, 1, 12, 0, 0),
                execution_time_ms=150.5,
                status="success",
                row_count=10,
                error_message=None,
            ),
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        # Act
        results = await query_history_repo.get_recent(limit=10)

        # Assert
        assert len(results) == 2
        assert results[0].id == 2  # Most recent first
        assert results[1].id == 1

    @pytest.mark.asyncio
    async def test_get_recent_with_custom_limit(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test retrieval with custom limit."""
        # Arrange
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        # Act
        results = await query_history_repo.get_recent(limit=5)

        # Assert
        assert results == []

    @pytest.mark.asyncio
    async def test_get_recent_database_error(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test handling of database errors during recent query retrieval."""
        # Arrange
        mock_session.execute.side_effect = SQLAlchemyError("Connection failed")

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to retrieve recent query history"):
            await query_history_repo.get_recent(limit=10)


class TestSearchQueries:
    """Tests for search_queries method."""

    @pytest.mark.asyncio
    async def test_search_queries_success(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test successful search of query history."""
        # Arrange
        mock_result = MagicMock()
        mock_rows = [
            MagicMock(
                id=1,
                query_text="SELECT * FROM users WHERE name LIKE '%John%'",
                executed_at=datetime(2025, 1, 1, 12, 0, 0),
                execution_time_ms=150.5,
                status="success",
                row_count=5,
                error_message=None,
            ),
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        # Act
        results = await query_history_repo.search_queries("users", limit=10)

        # Assert
        assert len(results) == 1
        assert "users" in results[0].query_text

    @pytest.mark.asyncio
    async def test_search_queries_no_results(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test search with no matching results."""
        # Arrange
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        # Act
        results = await query_history_repo.search_queries("nonexistent", limit=10)

        # Assert
        assert results == []

    @pytest.mark.asyncio
    async def test_search_queries_database_error(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test handling of database errors during search."""
        # Arrange
        mock_session.execute.side_effect = SQLAlchemyError("Connection timeout")

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to search query history"):
            await query_history_repo.search_queries("users", limit=10)


class TestDelete:
    """Tests for delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test successful deletion of query history."""
        # Arrange
        # Mock get_by_id to return a record
        mock_get_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.query_text = "SELECT * FROM users"
        mock_row.executed_at = datetime(2025, 1, 1, 12, 0, 0)
        mock_row.execution_time_ms = 150.5
        mock_row.status = "success"
        mock_row.row_count = 10
        mock_row.error_message = None
        mock_get_result.first.return_value = mock_row

        # Mock delete operation
        mock_delete_result = MagicMock()

        mock_session.execute.side_effect = [mock_get_result, mock_delete_result]

        # Act
        await query_history_repo.delete(1)

        # Assert
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test deletion when query history not found."""
        # Arrange
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ResourceNotFoundError, match="Query history not found"):
            await query_history_repo.delete(999)

    @pytest.mark.asyncio
    async def test_delete_database_error(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test handling of database errors during deletion."""
        # Arrange
        # First call for get_by_id succeeds
        mock_get_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.query_text = "SELECT * FROM users"
        mock_row.executed_at = datetime(2025, 1, 1, 12, 0, 0)
        mock_row.execution_time_ms = 150.5
        mock_row.status = "success"
        mock_row.row_count = 10
        mock_row.error_message = None
        mock_get_result.first.return_value = mock_row

        # Second call for delete fails
        mock_session.execute.side_effect = [
            mock_get_result,
            SQLAlchemyError("Connection failed"),
        ]

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to delete query history"):
            await query_history_repo.delete(1)

        mock_session.rollback.assert_called_once()


class TestCount:
    """Tests for count method."""

    @pytest.mark.asyncio
    async def test_count_success(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test successful count of query history records."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 42
        mock_session.execute.return_value = mock_result

        # Act
        count = await query_history_repo.count()

        # Assert
        assert count == 42

    @pytest.mark.asyncio
    async def test_count_empty_table(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test count when no records exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        # Act
        count = await query_history_repo.count()

        # Assert
        assert count == 0

    @pytest.mark.asyncio
    async def test_count_database_error(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test handling of database errors during count."""
        # Arrange
        mock_session.execute.side_effect = SQLAlchemyError("Connection failed")

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to count query history"):
            await query_history_repo.count()


class TestDeleteOldRecords:
    """Tests for delete_old_records method."""

    @pytest.mark.asyncio
    async def test_delete_old_records_success(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test successful deletion of old query history records."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        # Act
        deleted_count = await query_history_repo.delete_old_records(days=30)

        # Assert
        assert deleted_count == 5
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_old_records_none_deleted(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test deletion when no old records exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        # Act
        deleted_count = await query_history_repo.delete_old_records(days=30)

        # Assert
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_delete_old_records_database_error(
        self, query_history_repo: QueryHistoryRepository, mock_session: AsyncMock
    ) -> None:
        """Test handling of database errors during old record deletion."""
        # Arrange
        mock_session.execute.side_effect = SQLAlchemyError("Connection failed")

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to delete old query history"):
            await query_history_repo.delete_old_records(days=30)

        mock_session.rollback.assert_called_once()
