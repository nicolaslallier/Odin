"""Unit tests for log repository."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.api.exceptions import DatabaseError
from src.api.repositories.log_repository import LogRepository


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    return session


@pytest.fixture
def log_repo(mock_session):
    """Create a log repository instance."""
    return LogRepository(mock_session)


class TestLogRepository:
    """Tests for LogRepository class."""

    def test_initialization(self, mock_session):
        """Test repository initialization."""
        repo = LogRepository(mock_session)
        assert repo.session == mock_session

    @pytest.mark.asyncio
    async def test_get_logs_no_filters(self, log_repo, mock_session):
        """Test get_logs with no filters."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (
                1,
                datetime.now(timezone.utc),
                "INFO",
                "api",
                "test_logger",
                "Test message",
                "test_module",
                "test_func",
                42,
                None,
                None,
                None,
                None,
                {},
                datetime.now(timezone.utc),
            )
        ]
        mock_session.execute.return_value = mock_result

        logs = await log_repo.get_logs(limit=10, offset=0)

        assert len(logs) == 1
        assert logs[0]["level"] == "INFO"
        assert logs[0]["service"] == "api"
        assert logs[0]["message"] == "Test message"

    @pytest.mark.asyncio
    async def test_get_logs_with_time_filters(self, log_repo, mock_session):
        """Test get_logs with time range filters."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        start = datetime.now(timezone.utc) - timedelta(hours=1)
        end = datetime.now(timezone.utc)

        logs = await log_repo.get_logs(start_time=start, end_time=end)

        assert logs == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_logs_with_level_filter(self, log_repo, mock_session):
        """Test get_logs with level filter."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        logs = await log_repo.get_logs(level="ERROR")

        assert logs == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_logs_with_service_filter(self, log_repo, mock_session):
        """Test get_logs with service filter."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        logs = await log_repo.get_logs(service="api")

        assert logs == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_logs_with_search_filter(self, log_repo, mock_session):
        """Test get_logs with search filter."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        logs = await log_repo.get_logs(search="error")

        assert logs == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_logs_database_error(self, log_repo, mock_session):
        """Test get_logs handles database errors."""
        mock_session.execute.side_effect = SQLAlchemyError("Connection failed")

        with pytest.raises(DatabaseError, match="Failed to query logs"):
            await log_repo.get_logs()

    @pytest.mark.asyncio
    async def test_search_logs(self, log_repo, mock_session):
        """Test search_logs method."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (
                1,
                datetime.now(timezone.utc),
                "ERROR",
                "api",
                "logger",
                "Search term found",
                "module",
                "func",
                10,
                None,
                None,
                None,
                None,
                {},
                datetime.now(timezone.utc),
                0.5,  # rank column
            )
        ]
        mock_session.execute.return_value = mock_result

        logs = await log_repo.search_logs("search term", limit=10, offset=0)

        assert len(logs) == 1
        assert "Search term found" in logs[0]["message"]
        assert logs[0]["rank"] == 0.5

    @pytest.mark.asyncio
    async def test_search_logs_database_error(self, log_repo, mock_session):
        """Test search_logs handles database errors."""
        mock_session.execute.side_effect = SQLAlchemyError("Query failed")

        with pytest.raises(DatabaseError, match="Failed to search logs"):
            await log_repo.search_logs("term")

    @pytest.mark.asyncio
    async def test_get_log_statistics(self, log_repo, mock_session):
        """Test get_log_statistics method."""
        # First call: service/level stats
        mock_service_result = MagicMock()
        mock_service_result.fetchall.return_value = [
            ("api", "ERROR", 10, datetime.now(timezone.utc)),
            ("api", "INFO", 20, datetime.now(timezone.utc)),
            ("worker", "ERROR", 15, datetime.now(timezone.utc)),
        ]

        # Second call: total counts
        mock_total_result = MagicMock()
        mock_total_result.fetchone.return_value = (100, 5, 45, 30, 15, 5)

        mock_session.execute.side_effect = [
            mock_service_result,
            mock_total_result,
        ]

        start = datetime.now(timezone.utc) - timedelta(hours=1)
        end = datetime.now(timezone.utc)

        stats = await log_repo.get_log_statistics(start_time=start, end_time=end)

        assert stats["total_logs"] == 100
        assert "by_level" in stats
        assert stats["by_level"]["DEBUG"] == 5
        assert stats["by_level"]["INFO"] == 45
        assert stats["by_level"]["WARNING"] == 30
        assert stats["by_level"]["ERROR"] == 15
        assert stats["by_level"]["CRITICAL"] == 5
        assert "by_service" in stats
        assert "api" in stats["by_service"]
        assert stats["time_range"]["start"] == start.isoformat()
        assert stats["time_range"]["end"] == end.isoformat()

    @pytest.mark.asyncio
    async def test_get_log_statistics_no_time_range(self, log_repo, mock_session):
        """Test get_log_statistics without time range."""
        # First call: service/level stats
        mock_service_result = MagicMock()
        mock_service_result.fetchall.return_value = []

        # Second call: total counts
        mock_total_result = MagicMock()
        mock_total_result.fetchone.return_value = (50, 10, 20, 15, 4, 1)

        mock_session.execute.side_effect = [
            mock_service_result,
            mock_total_result,
        ]

        stats = await log_repo.get_log_statistics()

        assert stats["total_logs"] == 50
        assert "time_range" in stats
        assert "by_level" in stats
        assert "by_service" in stats

    @pytest.mark.asyncio
    async def test_cleanup_old_logs(self, log_repo, mock_session):
        """Test cleanup_old_logs method."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (42,)
        mock_session.execute.return_value = mock_result

        deleted_count = await log_repo.cleanup_old_logs(retention_days=30)

        assert deleted_count == 42
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_old_logs_database_error(self, log_repo, mock_session):
        """Test cleanup_old_logs handles database errors."""
        mock_session.execute.side_effect = SQLAlchemyError("Delete failed")

        with pytest.raises(DatabaseError, match="Failed to cleanup old logs"):
            await log_repo.cleanup_old_logs()

        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_related_logs(self, log_repo, mock_session):
        """Test get_related_logs method."""
        from uuid import uuid4
        
        test_request_id = uuid4()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (
                2,
                datetime.now(timezone.utc),
                "INFO",
                "api",
                "logger",
                "Related message",
                "module",
                "func",
                20,
                None,
                str(test_request_id),
                None,
                None,
                {},
                datetime.now(timezone.utc),
            )
        ]
        mock_session.execute.return_value = mock_result

        related = await log_repo.get_related_logs(request_id=test_request_id, limit=10)

        assert len(related) == 1
        assert str(test_request_id) in related[0]["request_id"]

    @pytest.mark.asyncio
    async def test_get_related_logs_no_ids(self, log_repo, mock_session):
        """Test get_related_logs without request_id or task_id."""
        # Should return empty list without querying
        related = await log_repo.get_related_logs()

        assert related == []
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_related_logs_database_error(self, log_repo, mock_session):
        """Test get_related_logs handles database errors."""
        from uuid import uuid4
        
        mock_session.execute.side_effect = SQLAlchemyError("Query failed")

        with pytest.raises(DatabaseError, match="Failed to get related logs"):
            await log_repo.get_related_logs(request_id=uuid4())

    @pytest.mark.asyncio
    async def test_get_log_by_id(self, log_repo, mock_session):
        """Test get_log_by_id method."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (
            1,
            datetime.now(timezone.utc),
            "ERROR",
            "api",
            "logger",
            "Error message",
            "module",
            "func",
            30,
            "Exception traceback",
            None,
            None,
            None,
            {"key": "value"},
            datetime.now(timezone.utc),
        )
        mock_session.execute.return_value = mock_result

        log = await log_repo.get_log_by_id(1)

        assert log is not None
        assert log["id"] == 1
        assert log["level"] == "ERROR"
        assert log["message"] == "Error message"
        assert log["exception"] == "Exception traceback"
        assert log["metadata"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_log_by_id_not_found(self, log_repo, mock_session):
        """Test get_log_by_id when log doesn't exist."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        log = await log_repo.get_log_by_id(999)

        assert log is None

    @pytest.mark.asyncio
    async def test_get_log_by_id_database_error(self, log_repo, mock_session):
        """Test get_log_by_id handles database errors."""
        mock_session.execute.side_effect = SQLAlchemyError("Query failed")

        with pytest.raises(DatabaseError, match="Failed to get log by ID"):
            await log_repo.get_log_by_id(1)

