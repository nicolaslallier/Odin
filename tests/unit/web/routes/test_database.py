"""Unit tests for database management web routes.

This module tests the web routes for the database management interface,
including the main page and all API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.services.db_management import DatabaseStats, QueryResult, TableInfo, TableSchema
from src.api.repositories.query_history_repository import QueryHistory


@pytest.fixture
def mock_db_service() -> MagicMock:
    """Create a mock database service.

    Returns:
        MagicMock for database service
    """
    return MagicMock()


@pytest.fixture
def mock_db_management_service() -> MagicMock:
    """Create a mock database management service.

    Returns:
        MagicMock for database management service
    """
    service = MagicMock()
    # Set up async methods
    service.get_all_tables = AsyncMock()
    service.get_table_schema = AsyncMock()
    service.execute_query = AsyncMock()
    service.get_table_data = AsyncMock()
    service.get_database_stats = AsyncMock()
    service.export_data = AsyncMock()
    return service


@pytest.fixture
def mock_query_history_repo() -> MagicMock:
    """Create a mock query history repository.

    Returns:
        MagicMock for query history repository
    """
    repo = MagicMock()
    repo.get_recent = AsyncMock()
    repo.search_queries = AsyncMock()
    repo.create = AsyncMock()
    return repo


@pytest.fixture
def app_with_mocks(
    mock_db_service: MagicMock,
    mock_db_management_service: MagicMock,
    mock_query_history_repo: MagicMock,
) -> FastAPI:
    """Create FastAPI app with mocked dependencies.

    Args:
        mock_db_service: Mock database service
        mock_db_management_service: Mock DB management service
        mock_query_history_repo: Mock query history repository

    Returns:
        FastAPI application with mocked dependencies
    """
    # Import here to avoid circular dependencies
    from src.web.routes.database import router
    from src.web.config import WebConfig
    from fastapi.templating import Jinja2Templates
    from pathlib import Path

    app = FastAPI()
    
    # Set up app state
    app.state.config = WebConfig(
        host="127.0.0.1",
        port=8000,
        api_base_url="http://localhost:8001",
    )
    
    # Set up templates
    templates_dir = Path(__file__).parent.parent.parent.parent / "src" / "web" / "templates"
    app.state.templates = Jinja2Templates(directory=str(templates_dir))
    
    # Store mocked services in app state
    app.state.db_service = mock_db_service
    app.state.db_management_service = mock_db_management_service
    app.state.query_history_repo = mock_query_history_repo
    
    app.include_router(router)
    return app


@pytest.fixture
def client(app_with_mocks: FastAPI) -> TestClient:
    """Create test client.

    Args:
        app_with_mocks: FastAPI app with mocked dependencies

    Returns:
        TestClient for making requests
    """
    return TestClient(app_with_mocks)


class TestDatabasePage:
    """Tests for main database management page."""

    def test_database_page_renders(self, client: TestClient) -> None:
        """Test that database page renders successfully."""
        # Act
        response = client.get("/database")

        # Assert
        assert response.status_code == 200
        assert "Database Management" in response.text or "database" in response.text.lower()


class TestGetTablesAPI:
    """Tests for get tables API endpoint."""

    @pytest.mark.asyncio
    async def test_get_tables_success(
        self, client: TestClient, app_with_mocks: FastAPI, mock_db_management_service: MagicMock
    ) -> None:
        """Test successful retrieval of tables."""
        # Arrange
        tables = [
            TableInfo(schema_name="public", table_name="users", row_count=100, size_bytes=8192),
            TableInfo(schema_name="public", table_name="posts", row_count=50, size_bytes=4096),
        ]
        mock_db_management_service.get_all_tables.return_value = tables

        # Act
        response = client.get("/database/tables")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["table_name"] == "users"
        assert data[0]["row_count"] == 100

    @pytest.mark.asyncio
    async def test_get_tables_empty(
        self, client: TestClient, app_with_mocks: FastAPI, mock_db_management_service: MagicMock
    ) -> None:
        """Test retrieval when no tables exist."""
        # Arrange
        mock_db_management_service.get_all_tables.return_value = []

        # Act
        response = client.get("/database/tables")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_tables_error(
        self, client: TestClient, app_with_mocks: FastAPI, mock_db_management_service: MagicMock
    ) -> None:
        """Test handling of errors during table retrieval."""
        # Arrange
        from src.api.exceptions import DatabaseError

        mock_db_management_service.get_all_tables.side_effect = DatabaseError("Connection failed")

        # Act
        response = client.get("/database/tables")

        # Assert
        assert response.status_code == 500
        assert "error" in response.json()


class TestGetTableSchemaAPI:
    """Tests for get table schema API endpoint."""

    @pytest.mark.asyncio
    async def test_get_table_schema_success(
        self, client: TestClient, app_with_mocks: FastAPI, mock_db_management_service: MagicMock
    ) -> None:
        """Test successful retrieval of table schema."""
        # Arrange
        schema = TableSchema(
            table_name="users",
            columns=[
                {"name": "id", "type": "integer", "nullable": True, "constraint": "PRIMARY KEY", "default": None},
                {"name": "username", "type": "varchar(100)", "nullable": False, "constraint": None, "default": None},
            ],
        )
        mock_db_management_service.get_table_schema.return_value = schema

        # Act
        response = client.get("/database/table/users")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["table_name"] == "users"
        assert len(data["columns"]) == 2

    @pytest.mark.asyncio
    async def test_get_table_schema_not_found(
        self, client: TestClient, app_with_mocks: FastAPI, mock_db_management_service: MagicMock
    ) -> None:
        """Test retrieval of non-existent table."""
        # Arrange
        from src.api.exceptions import DatabaseError

        mock_db_management_service.get_table_schema.side_effect = DatabaseError("Table not found")

        # Act
        response = client.get("/database/table/nonexistent")

        # Assert
        assert response.status_code == 500


class TestExecuteQueryAPI:
    """Tests for execute query API endpoint."""

    @pytest.mark.asyncio
    async def test_execute_query_select_success(
        self,
        client: TestClient,
        app_with_mocks: FastAPI,
        mock_db_management_service: MagicMock,
        mock_query_history_repo: MagicMock,
    ) -> None:
        """Test successful execution of SELECT query."""
        # Arrange
        result = QueryResult(
            success=True,
            row_count=2,
            columns=["id", "name"],
            rows=[[1, "John"], [2, "Jane"]],
            execution_time_ms=150.5,
        )
        mock_db_management_service.execute_query.return_value = result

        # Act
        response = client.post(
            "/database/query",
            json={"sql": "SELECT * FROM users", "confirmed": False},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["row_count"] == 2
        assert len(data["rows"]) == 2

    @pytest.mark.asyncio
    async def test_execute_query_validation_error(
        self, client: TestClient, app_with_mocks: FastAPI, mock_db_management_service: MagicMock
    ) -> None:
        """Test execution of query with validation error."""
        # Arrange
        from src.api.exceptions import ValidationError

        mock_db_management_service.execute_query.side_effect = ValidationError(
            "Destructive query requires confirmation"
        )

        # Act
        response = client.post(
            "/database/query",
            json={"sql": "DELETE FROM users", "confirmed": False},
        )

        # Assert
        assert response.status_code == 400
        assert "error" in response.json()

    @pytest.mark.asyncio
    async def test_execute_query_with_confirmation(
        self,
        client: TestClient,
        app_with_mocks: FastAPI,
        mock_db_management_service: MagicMock,
        mock_query_history_repo: MagicMock,
    ) -> None:
        """Test execution of destructive query with confirmation."""
        # Arrange
        result = QueryResult(
            success=True,
            row_count=5,
            columns=[],
            rows=[],
            execution_time_ms=200.0,
        )
        mock_db_management_service.execute_query.return_value = result

        # Act
        response = client.post(
            "/database/query",
            json={"sql": "DELETE FROM users WHERE id < 10", "confirmed": True},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["row_count"] == 5


class TestGetTableDataAPI:
    """Tests for get table data API endpoint."""

    @pytest.mark.asyncio
    async def test_get_table_data_success(
        self, client: TestClient, app_with_mocks: FastAPI, mock_db_management_service: MagicMock
    ) -> None:
        """Test successful retrieval of table data."""
        # Arrange
        result = QueryResult(
            success=True,
            row_count=2,
            columns=["id", "name"],
            rows=[[1, "John"], [2, "Jane"]],
        )
        mock_db_management_service.get_table_data.return_value = result

        # Act
        response = client.get("/database/table/users/data?page=1&page_size=10")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["rows"]) == 2

    @pytest.mark.asyncio
    async def test_get_table_data_with_search(
        self, client: TestClient, app_with_mocks: FastAPI, mock_db_management_service: MagicMock
    ) -> None:
        """Test table data retrieval with search filter."""
        # Arrange
        result = QueryResult(
            success=True,
            row_count=1,
            columns=["id", "name"],
            rows=[[1, "John"]],
        )
        mock_db_management_service.get_table_data.return_value = result

        # Act
        response = client.get("/database/table/users/data?page=1&page_size=10&search=John")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["row_count"] == 1


class TestGetDatabaseStatsAPI:
    """Tests for get database stats API endpoint."""

    @pytest.mark.asyncio
    async def test_get_database_stats_success(
        self, client: TestClient, app_with_mocks: FastAPI, mock_db_management_service: MagicMock
    ) -> None:
        """Test successful retrieval of database statistics."""
        # Arrange
        stats = DatabaseStats(
            database_size_bytes=10485760,
            version="PostgreSQL 15.3",
            connection_count=5,
        )
        mock_db_management_service.get_database_stats.return_value = stats

        # Act
        response = client.get("/database/stats")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["database_size_bytes"] == 10485760
        assert "PostgreSQL" in data["version"]
        assert data["connection_count"] == 5

    @pytest.mark.asyncio
    async def test_get_database_stats_error(
        self, client: TestClient, app_with_mocks: FastAPI, mock_db_management_service: MagicMock
    ) -> None:
        """Test handling of errors during stats retrieval."""
        # Arrange
        from src.api.exceptions import DatabaseError

        mock_db_management_service.get_database_stats.side_effect = DatabaseError("Connection failed")

        # Act
        response = client.get("/database/stats")

        # Assert
        assert response.status_code == 500


class TestExportDataAPI:
    """Tests for export data API endpoint."""

    @pytest.mark.asyncio
    async def test_export_data_csv(
        self, client: TestClient, app_with_mocks: FastAPI, mock_db_management_service: MagicMock
    ) -> None:
        """Test data export in CSV format."""
        # Arrange
        mock_db_management_service.export_data.return_value = "id,name\n1,John\n2,Jane\n"

        # Act
        response = client.get("/database/export?query=SELECT * FROM users&format=csv")

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "id,name" in response.text

    @pytest.mark.asyncio
    async def test_export_data_json(
        self, client: TestClient, app_with_mocks: FastAPI, mock_db_management_service: MagicMock
    ) -> None:
        """Test data export in JSON format."""
        # Arrange
        mock_db_management_service.export_data.return_value = '[{"id": 1, "name": "John"}]'

        # Act
        response = client.get("/database/export?query=SELECT * FROM users&format=json")

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_export_data_invalid_format(
        self, client: TestClient, app_with_mocks: FastAPI, mock_db_management_service: MagicMock
    ) -> None:
        """Test export with invalid format."""
        # Arrange
        from src.api.exceptions import ValidationError

        mock_db_management_service.export_data.side_effect = ValidationError("Unsupported format")

        # Act
        response = client.get("/database/export?query=SELECT * FROM users&format=xml")

        # Assert
        assert response.status_code == 400


class TestGetQueryHistoryAPI:
    """Tests for get query history API endpoint."""

    @pytest.mark.asyncio
    async def test_get_query_history_success(
        self, client: TestClient, app_with_mocks: FastAPI, mock_query_history_repo: MagicMock
    ) -> None:
        """Test successful retrieval of query history."""
        # Arrange
        history = [
            QueryHistory(
                id=1,
                query_text="SELECT * FROM users",
                executed_at=datetime(2025, 1, 1, 12, 0, 0),
                execution_time_ms=150.5,
                status="success",
                row_count=10,
                error_message=None,
            ),
        ]
        mock_query_history_repo.get_recent.return_value = history

        # Act
        response = client.get("/database/history?limit=10")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["query_text"] == "SELECT * FROM users"

    @pytest.mark.asyncio
    async def test_get_query_history_with_search(
        self, client: TestClient, app_with_mocks: FastAPI, mock_query_history_repo: MagicMock
    ) -> None:
        """Test query history search."""
        # Arrange
        history = [
            QueryHistory(
                id=1,
                query_text="SELECT * FROM users WHERE name LIKE '%John%'",
                executed_at=datetime(2025, 1, 1, 12, 0, 0),
                execution_time_ms=150.5,
                status="success",
                row_count=5,
                error_message=None,
            ),
        ]
        mock_query_history_repo.search_queries.return_value = history

        # Act
        response = client.get("/database/history?limit=10&search=users")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "users" in data[0]["query_text"]

