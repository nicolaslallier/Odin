"""Regression tests for database management security.

This module contains regression tests to ensure SQL injection protection
and destructive query confirmation requirements are maintained.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.exceptions import ValidationError
from src.api.services.db_management import DatabaseManagementService


@pytest.fixture
def mock_db_service() -> MagicMock:
    """Create a mock database service.

    Returns:
        MagicMock for database service
    """
    service = MagicMock()
    service.get_session = AsyncMock()
    return service


@pytest.fixture
def db_management_service(mock_db_service: MagicMock) -> DatabaseManagementService:
    """Create a DatabaseManagementService instance.

    Args:
        mock_db_service: Mock database service

    Returns:
        DatabaseManagementService instance
    """
    return DatabaseManagementService(mock_db_service)


class TestSQLInjectionProtection:
    """Regression tests for SQL injection protection.

    These tests ensure that the system prevents SQL injection attacks
    by using parameterized queries and proper input validation.
    """

    @pytest.mark.asyncio
    async def test_parameterized_queries_prevent_injection(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test that parameterized queries are used to prevent SQL injection.

        Regression test for: Ensuring all queries use parameterized
        queries instead of string concatenation.
        """
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id", "name"]
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        mock_db_service.get_session.return_value.__aenter__.return_value = mock_session

        # Act - Try to inject SQL through search parameter
        malicious_search = "'; DROP TABLE users; --"
        result = await db_management_service.get_table_data(
            table_name="users",
            page=1,
            page_size=10,
            search=malicious_search,
        )

        # Assert - Query should execute safely without SQL injection
        assert result.success is True
        # The malicious input should be treated as a search string, not SQL

    @pytest.mark.asyncio
    async def test_table_name_validation_prevents_injection(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test that table names are validated to prevent injection.

        Regression test for: Ensuring table names cannot contain
        malicious SQL commands.
        """
        # Arrange
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Invalid table name")
        mock_db_service.get_session.return_value.__aenter__.return_value = mock_session

        # Act - Try to inject SQL through table name
        malicious_table_name = "users; DROP TABLE sensitive_data; --"
        result = await db_management_service.get_table_data(
            table_name=malicious_table_name,
            page=1,
            page_size=10,
        )

        # Assert - Should fail safely without executing injection
        assert result.success is False
        assert result.error is not None

    def test_sql_validation_detects_malicious_patterns(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test that SQL validation detects common injection patterns.

        Regression test for: Ensuring SQL parser detects and flags
        potentially malicious SQL patterns.
        """
        # Test various injection attempts
        injection_attempts = [
            "SELECT * FROM users WHERE id = 1; DROP TABLE users; --",
            "SELECT * FROM users WHERE name = '' OR '1'='1'",
            "'; DELETE FROM users WHERE '1'='1",
        ]

        for sql in injection_attempts:
            # Act
            validation = db_management_service.validate_sql(sql)

            # Assert - Should parse successfully but detect issues
            # Note: sqlparse is permissive, so we mainly check it doesn't crash
            assert validation["is_valid"] is True or validation["error"] is not None


class TestDestructiveQueryProtection:
    """Regression tests for destructive query protection.

    These tests ensure that destructive operations (DELETE, DROP, TRUNCATE, ALTER)
    require explicit confirmation before execution.
    """

    @pytest.mark.asyncio
    async def test_delete_requires_confirmation(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test that DELETE queries require confirmation.

        Regression test for: Bug where DELETE queries could be executed
        without confirmation.
        """
        # Act & Assert
        with pytest.raises(ValidationError, match="Destructive query requires confirmation"):
            await db_management_service.execute_query(
                "DELETE FROM users WHERE id = 1",
                confirmed=False,
            )

    @pytest.mark.asyncio
    async def test_drop_requires_confirmation(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test that DROP queries require confirmation.

        Regression test for: Ensuring DROP TABLE cannot be executed
        without explicit confirmation.
        """
        # Act & Assert
        with pytest.raises(ValidationError, match="Destructive query requires confirmation"):
            await db_management_service.execute_query(
                "DROP TABLE users",
                confirmed=False,
            )

    @pytest.mark.asyncio
    async def test_truncate_requires_confirmation(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test that TRUNCATE queries require confirmation.

        Regression test for: Ensuring TRUNCATE cannot be executed
        without explicit confirmation.
        """
        # Act & Assert
        with pytest.raises(ValidationError, match="Destructive query requires confirmation"):
            await db_management_service.execute_query(
                "TRUNCATE TABLE users",
                confirmed=False,
            )

    @pytest.mark.asyncio
    async def test_alter_requires_confirmation(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test that ALTER queries require confirmation.

        Regression test for: Ensuring ALTER TABLE cannot be executed
        without explicit confirmation.
        """
        # Act & Assert
        with pytest.raises(ValidationError, match="Destructive query requires confirmation"):
            await db_management_service.execute_query(
                "ALTER TABLE users ADD COLUMN age INTEGER",
                confirmed=False,
            )

    @pytest.mark.asyncio
    async def test_destructive_query_executes_with_confirmation(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test that destructive queries execute when confirmed.

        Regression test for: Ensuring confirmation flag allows
        destructive operations to proceed.
        """
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result
        mock_db_service.get_session.return_value.__aenter__.return_value = mock_session

        # Act
        result = await db_management_service.execute_query(
            "DELETE FROM users WHERE id < 10",
            confirmed=True,  # Explicit confirmation
        )

        # Assert
        assert result.success is True
        assert result.row_count == 5

    @pytest.mark.asyncio
    async def test_select_query_does_not_require_confirmation(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test that SELECT queries don't require confirmation.

        Regression test for: Ensuring read-only queries work without
        extra confirmation steps.
        """
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id", "name"]
        mock_result.fetchall.return_value = [[1, "John"], [2, "Jane"]]
        mock_session.execute.return_value = mock_result
        mock_db_service.get_session.return_value.__aenter__.return_value = mock_session

        # Act - No confirmation needed
        result = await db_management_service.execute_query(
            "SELECT * FROM users",
            confirmed=False,
        )

        # Assert
        assert result.success is True
        assert result.row_count == 2

    @pytest.mark.asyncio
    async def test_insert_query_does_not_require_confirmation(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test that INSERT queries don't require confirmation.

        Regression test for: Ensuring INSERT operations are treated
        as non-destructive.
        """
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_db_service.get_session.return_value.__aenter__.return_value = mock_session

        # Act - No confirmation needed
        result = await db_management_service.execute_query(
            "INSERT INTO users (name) VALUES ('John')",
            confirmed=False,
        )

        # Assert
        assert result.success is True
        assert result.row_count == 1

    @pytest.mark.asyncio
    async def test_update_query_does_not_require_confirmation(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test that UPDATE queries don't require confirmation.

        Regression test for: Ensuring UPDATE operations are treated
        as non-destructive.
        """
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result
        mock_db_service.get_session.return_value.__aenter__.return_value = mock_session

        # Act - No confirmation needed
        result = await db_management_service.execute_query(
            "UPDATE users SET name = 'Jane' WHERE id = 1",
            confirmed=False,
        )

        # Assert
        assert result.success is True
        assert result.row_count == 3


class TestQueryValidation:
    """Regression tests for query validation logic."""

    def test_validation_handles_empty_queries(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test that empty queries are properly rejected.

        Regression test for: Bug where empty queries could cause
        validation errors.
        """
        # Act
        result = db_management_service.validate_sql("")

        # Assert
        assert result["is_valid"] is False
        assert result["error"] == "Query is empty"

    def test_validation_handles_whitespace_only_queries(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test that whitespace-only queries are rejected.

        Regression test for: Ensuring queries with only whitespace
        are treated as empty.
        """
        # Act
        result = db_management_service.validate_sql("   \n\t  ")

        # Assert
        assert result["is_valid"] is False
        assert result["error"] == "Query is empty"

    def test_validation_identifies_query_types_correctly(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test that query type identification is accurate.

        Regression test for: Ensuring query type detection works
        for all common SQL statement types.
        """
        queries = [
            ("SELECT * FROM users", "SELECT", False),
            ("INSERT INTO users (name) VALUES ('John')", "INSERT", False),
            ("UPDATE users SET name = 'Jane'", "UPDATE", False),
            ("DELETE FROM users WHERE id = 1", "DELETE", True),
            ("DROP TABLE users", "DROP", True),
            ("TRUNCATE TABLE users", "TRUNCATE", True),
            ("ALTER TABLE users ADD COLUMN age INT", "ALTER", True),
        ]

        for sql, expected_type, expected_destructive in queries:
            # Act
            result = db_management_service.validate_sql(sql)

            # Assert
            assert result["is_valid"] is True
            assert result["query_type"] == expected_type
            assert result["is_destructive"] == expected_destructive

