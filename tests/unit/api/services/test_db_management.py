"""Unit tests for database management service.

This module tests the DatabaseManagementService class which provides
comprehensive PostgreSQL database administration capabilities.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.api.exceptions import DatabaseError, ValidationError
from src.api.services.db_management import (
    DatabaseManagementService,
)


@pytest.fixture
def mock_db_service() -> MagicMock:
    """Create a mock database service.

    Returns:
        MagicMock instance configured for database operations
    """
    from unittest.mock import AsyncMock as AM

    service = MagicMock()

    # Create a proper async context manager that can be configured per test
    class MockAsyncContextManager:
        def __init__(self):
            self.session = AM()

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    # Store the instance so tests can configure the session
    service._mock_cm = MockAsyncContextManager()
    service.get_session.return_value = service._mock_cm

    return service


@pytest.fixture
def db_management_service(mock_db_service: MagicMock) -> DatabaseManagementService:
    """Create a DatabaseManagementService instance with mocked dependencies.

    Args:
        mock_db_service: Mock database service

    Returns:
        DatabaseManagementService instance for testing
    """
    return DatabaseManagementService(mock_db_service)


class TestGetAllTables:
    """Tests for get_all_tables method."""

    @pytest.mark.asyncio
    async def test_get_all_tables_success(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test successful retrieval of all tables."""
        # Arrange
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("public", "users", 100, 8192),
            ("public", "posts", 50, 4096),
        ]
        mock_db_service._mock_cm.session.execute.return_value = mock_result

        # Act
        tables = await db_management_service.get_all_tables()

        # Assert
        assert len(tables) == 2
        assert tables[0].schema_name == "public"
        assert tables[0].table_name == "users"
        assert tables[0].row_count == 100
        assert tables[0].size_bytes == 8192
        assert tables[1].table_name == "posts"

    @pytest.mark.asyncio
    async def test_get_all_tables_empty_database(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test retrieval when database has no tables."""
        # Arrange
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db_service._mock_cm.session.execute.return_value = mock_result

        # Act
        tables = await db_management_service.get_all_tables()

        # Assert
        assert tables == []

    @pytest.mark.asyncio
    async def test_get_all_tables_database_error(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test handling of database errors during table retrieval."""
        # Arrange
        mock_db_service._mock_cm.session.execute.side_effect = SQLAlchemyError("Connection failed")

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to retrieve tables"):
            await db_management_service.get_all_tables()


class TestGetTableSchema:
    """Tests for get_table_schema method."""

    @pytest.mark.asyncio
    async def test_get_table_schema_success(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test successful retrieval of table schema."""
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("id", "integer", True, "PRIMARY KEY", "nextval('users_id_seq'::regclass)"),
            ("username", "character varying(100)", False, "UNIQUE", None),
            ("email", "character varying(255)", False, None, None),
            ("created_at", "timestamp without time zone", False, None, "CURRENT_TIMESTAMP"),
        ]
        mock_session.execute.return_value = mock_result
        mock_db_service._mock_cm.session = mock_session

        # Act
        schema = await db_management_service.get_table_schema("users")

        # Assert
        assert schema.table_name == "users"
        assert len(schema.columns) == 4
        assert schema.columns[0]["name"] == "id"
        assert schema.columns[0]["type"] == "integer"
        assert schema.columns[0]["nullable"] is True
        assert schema.columns[0]["constraint"] == "PRIMARY KEY"
        assert schema.columns[1]["name"] == "username"
        assert schema.columns[1]["constraint"] == "UNIQUE"

    @pytest.mark.asyncio
    async def test_get_table_schema_table_not_found(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test handling when table doesn't exist."""
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        mock_db_service._mock_cm.session = mock_session

        # Act & Assert
        with pytest.raises(DatabaseError, match="Table .* not found"):
            await db_management_service.get_table_schema("nonexistent_table")

    @pytest.mark.asyncio
    async def test_get_table_schema_database_error(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test handling of database errors during schema retrieval."""
        # Arrange
        mock_session = AsyncMock()
        mock_session.execute.side_effect = SQLAlchemyError("Connection timeout")
        mock_db_service._mock_cm.session = mock_session

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to retrieve table schema"):
            await db_management_service.get_table_schema("users")


class TestValidateSQL:
    """Tests for validate_sql method."""

    def test_validate_sql_select_query(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test validation of SELECT query."""
        # Act
        result = db_management_service.validate_sql("SELECT * FROM users")

        # Assert
        assert result["is_valid"] is True
        assert result["is_destructive"] is False
        assert result["query_type"] == "SELECT"
        assert result["error"] is None

    def test_validate_sql_insert_query(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test validation of INSERT query."""
        # Act
        result = db_management_service.validate_sql("INSERT INTO users (name) VALUES ('John')")

        # Assert
        assert result["is_valid"] is True
        assert result["is_destructive"] is False
        assert result["query_type"] == "INSERT"

    def test_validate_sql_update_query(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test validation of UPDATE query."""
        # Act
        result = db_management_service.validate_sql("UPDATE users SET name = 'Jane' WHERE id = 1")

        # Assert
        assert result["is_valid"] is True
        assert result["is_destructive"] is False
        assert result["query_type"] == "UPDATE"

    def test_validate_sql_delete_query(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test validation of DELETE query (destructive)."""
        # Act
        result = db_management_service.validate_sql("DELETE FROM users WHERE id = 1")

        # Assert
        assert result["is_valid"] is True
        assert result["is_destructive"] is True
        assert result["query_type"] == "DELETE"

    def test_validate_sql_drop_query(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test validation of DROP query (destructive)."""
        # Act
        result = db_management_service.validate_sql("DROP TABLE users")

        # Assert
        assert result["is_valid"] is True
        assert result["is_destructive"] is True
        assert result["query_type"] == "DROP"

    def test_validate_sql_truncate_query(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test validation of TRUNCATE query (destructive)."""
        # Act
        result = db_management_service.validate_sql("TRUNCATE TABLE users")

        # Assert
        assert result["is_valid"] is True
        assert result["is_destructive"] is True
        assert result["query_type"] == "TRUNCATE"

    def test_validate_sql_alter_query(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test validation of ALTER query (destructive)."""
        # Act
        result = db_management_service.validate_sql("ALTER TABLE users ADD COLUMN age INTEGER")

        # Assert
        assert result["is_valid"] is True
        assert result["is_destructive"] is True
        assert result["query_type"] == "ALTER"

    def test_validate_sql_empty_query(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test validation of empty query."""
        # Act
        result = db_management_service.validate_sql("")

        # Assert
        assert result["is_valid"] is False
        assert result["error"] == "Query is empty"

    def test_validate_sql_invalid_syntax(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test validation of query with invalid syntax."""
        # Act
        result = db_management_service.validate_sql("SELEKT * FROM users")

        # Assert
        # sqlparse is permissive, so it may still parse this
        # We mainly check for empty or malformed queries
        assert result["is_valid"] is True  # sqlparse accepts this
        assert result["query_type"] == "UNKNOWN"


class TestExecuteQuery:
    """Tests for execute_query method."""

    @pytest.mark.asyncio
    async def test_execute_query_select_success(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test successful execution of SELECT query."""
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id", "name", "email"]
        mock_result.fetchall.return_value = [
            (1, "John Doe", "john@example.com"),
            (2, "Jane Smith", "jane@example.com"),
        ]
        mock_session.execute.return_value = mock_result
        mock_db_service._mock_cm.session = mock_session

        # Act
        result = await db_management_service.execute_query("SELECT * FROM users", confirmed=False)

        # Assert
        assert result.success is True
        assert result.row_count == 2
        assert result.columns == ["id", "name", "email"]
        assert len(result.rows) == 2
        assert result.rows[0] == [1, "John Doe", "john@example.com"]
        assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_query_insert_success(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test successful execution of INSERT query."""
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_db_service._mock_cm.session = mock_session

        # Act
        result = await db_management_service.execute_query(
            "INSERT INTO users (name) VALUES ('John')", confirmed=False
        )

        # Assert
        assert result.success is True
        assert result.row_count == 1
        assert result.columns == []
        assert result.rows == []

    @pytest.mark.asyncio
    async def test_execute_query_destructive_without_confirmation(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test that destructive query requires confirmation."""
        # Act & Assert
        with pytest.raises(ValidationError, match="Destructive query requires confirmation"):
            await db_management_service.execute_query("DELETE FROM users", confirmed=False)

    @pytest.mark.asyncio
    async def test_execute_query_destructive_with_confirmation(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test successful execution of destructive query with confirmation."""
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result
        mock_db_service._mock_cm.session = mock_session

        # Act
        result = await db_management_service.execute_query(
            "DELETE FROM users WHERE id < 10", confirmed=True
        )

        # Assert
        assert result.success is True
        assert result.row_count == 5

    @pytest.mark.asyncio
    async def test_execute_query_database_error(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test handling of database errors during query execution."""
        # Arrange
        mock_session = AsyncMock()
        mock_session.execute.side_effect = SQLAlchemyError("Syntax error")
        mock_db_service._mock_cm.session = mock_session

        # Act
        result = await db_management_service.execute_query("SELECT * FROM invalid", confirmed=False)

        # Assert
        assert result.success is False
        assert result.error is not None
        assert "Syntax error" in result.error

    @pytest.mark.asyncio
    async def test_execute_query_timeout(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test handling of query timeout."""
        # Arrange
        mock_session = AsyncMock()
        mock_session.execute.side_effect = TimeoutError("Query timeout")
        mock_db_service._mock_cm.session = mock_session

        # Act
        result = await db_management_service.execute_query(
            "SELECT * FROM large_table", confirmed=False
        )

        # Assert
        assert result.success is False
        assert result.error is not None
        assert "timeout" in result.error.lower()


class TestGetTableData:
    """Tests for get_table_data method."""

    @pytest.mark.asyncio
    async def test_get_table_data_success(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test successful retrieval of table data with pagination."""
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id", "name"]
        mock_result.fetchall.return_value = [
            (1, "John"),
            (2, "Jane"),
        ]
        mock_session.execute.return_value = mock_result
        mock_db_service._mock_cm.session = mock_session

        # Act
        result = await db_management_service.get_table_data("users", page=1, page_size=10)

        # Assert
        assert result.success is True
        assert result.row_count == 2
        assert len(result.rows) == 2

    @pytest.mark.asyncio
    async def test_get_table_data_with_search(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test table data retrieval with search filter."""
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id", "name"]
        mock_result.fetchall.return_value = [(1, "John")]
        mock_session.execute.return_value = mock_result
        mock_db_service._mock_cm.session = mock_session

        # Act
        result = await db_management_service.get_table_data(
            "users", page=1, page_size=10, search="John"
        )

        # Assert
        assert result.success is True
        assert result.row_count == 1

    @pytest.mark.asyncio
    async def test_get_table_data_with_order_by(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test table data retrieval with custom ordering."""
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id", "name"]
        mock_result.fetchall.return_value = [(2, "Jane"), (1, "John")]
        mock_session.execute.return_value = mock_result
        mock_db_service._mock_cm.session = mock_session

        # Act
        result = await db_management_service.get_table_data(
            "users", page=1, page_size=10, order_by="name DESC"
        )

        # Assert
        assert result.success is True
        assert result.rows[0][1] == "Jane"  # First by name DESC

    @pytest.mark.asyncio
    async def test_get_table_data_with_binary_data(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test get_table_data handling binary data (bytes and memoryview)."""
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id", "data", "buffer"]
        mock_result.fetchall.return_value = [
            (1, b"binary_content", memoryview(b"buffer_content")),
        ]
        mock_session.execute.return_value = mock_result
        mock_db_service._mock_cm.session = mock_session

        # Act
        result = await db_management_service.get_table_data("test_table")

        # Assert
        assert result.success is True
        assert result.rows[0][0] == 1
        assert result.rows[0][1] == "<binary: 14 bytes>"
        assert result.rows[0][2] == "<binary: 14 bytes>"

    @pytest.mark.asyncio
    async def test_get_table_data_exception(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test get_table_data exception handling."""
        # Arrange
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database error")
        mock_db_service._mock_cm.session = mock_session

        # Act
        result = await db_management_service.get_table_data("test_table")

        # Assert
        assert result.success is False
        assert result.row_count == 0
        assert "Database error" in result.error


class TestGetDatabaseStats:
    """Tests for get_database_stats method."""

    @pytest.mark.asyncio
    async def test_get_database_stats_success(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test successful retrieval of database statistics."""
        # Arrange
        mock_session = AsyncMock()

        # Mock database size query
        mock_size_result = MagicMock()
        mock_size_result.scalar.return_value = 10485760  # 10 MB

        # Mock version query
        mock_version_result = MagicMock()
        mock_version_result.scalar.return_value = "PostgreSQL 15.3"

        # Mock connection count query
        mock_conn_result = MagicMock()
        mock_conn_result.scalar.return_value = 5

        mock_session.execute.side_effect = [mock_size_result, mock_version_result, mock_conn_result]
        mock_db_service._mock_cm.session = mock_session

        # Act
        stats = await db_management_service.get_database_stats()

        # Assert
        assert stats.database_size_bytes == 10485760
        assert stats.version == "PostgreSQL 15.3"
        assert stats.connection_count == 5

    @pytest.mark.asyncio
    async def test_get_database_stats_error(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test handling of errors during stats retrieval."""
        # Arrange
        mock_session = AsyncMock()
        mock_session.execute.side_effect = SQLAlchemyError("Connection failed")
        mock_db_service._mock_cm.session = mock_session

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to retrieve database statistics"):
            await db_management_service.get_database_stats()


class TestExportData:
    """Tests for export_data method."""

    @pytest.mark.asyncio
    async def test_export_data_as_csv(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test data export in CSV format."""
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id", "name"]
        mock_result.fetchall.return_value = [(1, "John"), (2, "Jane")]
        mock_session.execute.return_value = mock_result
        mock_db_service._mock_cm.session = mock_session

        # Act
        content = await db_management_service.export_data("SELECT * FROM users", format="csv")

        # Assert
        assert "id,name" in content
        assert "1,John" in content
        assert "2,Jane" in content

    @pytest.mark.asyncio
    async def test_export_data_as_json(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test data export in JSON format."""
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id", "name"]
        mock_result.fetchall.return_value = [(1, "John"), (2, "Jane")]
        mock_session.execute.return_value = mock_result
        mock_db_service._mock_cm.session = mock_session

        # Act
        content = await db_management_service.export_data("SELECT * FROM users", format="json")

        # Assert
        assert '"id": 1' in content or '"id":1' in content
        assert '"name": "John"' in content or '"name":"John"' in content

    @pytest.mark.asyncio
    async def test_export_data_invalid_format(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test export with invalid format."""
        # Act & Assert
        with pytest.raises(ValidationError, match="Unsupported export format"):
            await db_management_service.export_data("SELECT * FROM users", format="xml")

    @pytest.mark.asyncio
    async def test_export_data_query_error(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test export when query fails."""
        # Arrange
        mock_session = AsyncMock()
        mock_session.execute.side_effect = SQLAlchemyError("Invalid query")
        mock_db_service._mock_cm.session = mock_session

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to export data"):
            await db_management_service.export_data("SELECT * FROM invalid", format="csv")

    @pytest.mark.asyncio
    async def test_execute_query_with_binary_data(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test execute_query handling binary data (bytes and memoryview)."""
        # Arrange
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.returns_rows = True
        mock_result.keys.return_value = ["id", "data", "buffer"]
        mock_result.fetchall.return_value = [(1, b"binary_data_here", memoryview(b"buffer_data"))]
        mock_session.execute.return_value = mock_result
        mock_db_service._mock_cm.session = mock_session

        # Act
        result = await db_management_service.execute_query("SELECT * FROM test", confirmed=True)

        # Assert
        assert result.success is True
        assert result.row_count == 1
        assert result.rows[0][0] == 1
        assert result.rows[0][1] == "<binary: 16 bytes>"
        assert result.rows[0][2] == "<binary: 11 bytes>"


class TestValidateSQL:
    """Tests for validate_sql method."""

    def test_validate_sql_empty_query(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test validate_sql with empty query."""
        result = db_management_service.validate_sql("")

        assert result["is_valid"] is False
        assert result["error"] == "Query is empty"
        assert result["query_type"] == "UNKNOWN"

    def test_validate_sql_whitespace_only_query(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test validate_sql with whitespace-only query."""
        result = db_management_service.validate_sql("   \n\t  ")

        assert result["is_valid"] is False
        assert result["error"] == "Query is empty"
        assert result["query_type"] == "UNKNOWN"

    def test_validate_sql_empty_parse_result(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test validate_sql with query that fails to parse."""
        import unittest.mock as mock

        with mock.patch("sqlparse.parse", return_value=[]):
            result = db_management_service.validate_sql("INVALID SQL;;;")

            assert result["is_valid"] is False
            assert result["error"] == "Failed to parse query"
            assert result["query_type"] == "UNKNOWN"

    def test_validate_sql_none_query_type(
        self, db_management_service: DatabaseManagementService
    ) -> None:
        """Test validate_sql when statement.get_type() returns None."""
        import unittest.mock as mock

        mock_statement = mock.MagicMock()
        mock_statement.get_type.return_value = None
        mock_statement.tokens = []

        with mock.patch("sqlparse.parse", return_value=[mock_statement]):
            result = db_management_service.validate_sql("SELECT 1")

            assert result["is_valid"] is True
            assert result["query_type"] == "UNKNOWN"

    def test_validate_sql_exception(self, db_management_service: DatabaseManagementService) -> None:
        """Test validate_sql exception handling."""
        import unittest.mock as mock

        with mock.patch("sqlparse.parse", side_effect=Exception("Parse error")):
            result = db_management_service.validate_sql("SELECT * FROM test")

            assert result["is_valid"] is False
            assert result["query_type"] == "UNKNOWN"
            assert "Parse error" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_query_invalid_sql(
        self, db_management_service: DatabaseManagementService, mock_db_service: MagicMock
    ) -> None:
        """Test execute_query with invalid SQL."""
        import unittest.mock as mock

        # Mock validate_sql to return invalid
        with mock.patch.object(
            db_management_service,
            "validate_sql",
            return_value={
                "is_valid": False,
                "is_destructive": False,
                "query_type": "UNKNOWN",
                "error": "Syntax error",
            },
        ):
            result = await db_management_service.execute_query("INVALID SQL")

            assert result.success is False
            assert result.row_count == 0
            assert result.error == "Syntax error"
