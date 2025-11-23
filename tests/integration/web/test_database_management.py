"""Integration tests for database management functionality.

This module tests the end-to-end database management flow including
page rendering, API interactions, and data persistence.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Create test client with real app instance.

    Returns:
        TestClient for making requests
    """
    app = create_app()
    return TestClient(app)


class TestDatabasePageIntegration:
    """Integration tests for database management page."""

    def test_database_page_loads(self, client: TestClient) -> None:
        """Test that database management page loads successfully."""
        # Act
        response = client.get("/database")

        # Assert
        assert response.status_code == 200
        assert "database" in response.text.lower()

    def test_database_page_has_tabs(self, client: TestClient) -> None:
        """Test that database page contains all required tabs."""
        # Act
        response = client.get("/database")
        content = response.text.lower()

        # Assert
        assert "tables" in content
        assert "query" in content
        assert "statistics" in content
        assert "history" in content

    def test_database_page_has_css_and_js(self, client: TestClient) -> None:
        """Test that database page includes CSS and JavaScript."""
        # Act
        response = client.get("/database")
        content = response.text

        # Assert
        assert "database.css" in content
        assert "database.js" in content


class TestDatabaseAPIIntegration:
    """Integration tests for database API endpoints."""

    @patch("src.web.routes.database.get_db_management_service")
    def test_get_tables_api(
        self, mock_get_service: MagicMock, client: TestClient
    ) -> None:
        """Test tables API endpoint returns data."""
        # Arrange
        from src.api.services.db_management import TableInfo

        mock_service = MagicMock()
        mock_service.get_all_tables = AsyncMock(
            return_value=[
                TableInfo(
                    schema_name="public",
                    table_name="test_table",
                    row_count=10,
                    size_bytes=1024,
                )
            ]
        )
        mock_get_service.return_value = mock_service

        # Act
        response = client.get("/database/tables")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["table_name"] == "test_table"

    @patch("src.web.routes.database.get_db_management_service")
    def test_execute_query_api(
        self, mock_get_service: MagicMock, client: TestClient
    ) -> None:
        """Test query execution API endpoint."""
        # Arrange
        from src.api.services.db_management import QueryResult

        mock_service = MagicMock()
        mock_service.execute_query = AsyncMock(
            return_value=QueryResult(
                success=True,
                row_count=2,
                columns=["id", "name"],
                rows=[[1, "John"], [2, "Jane"]],
                execution_time_ms=150.5,
            )
        )
        mock_get_service.return_value = mock_service

        # Mock database service for history
        with patch("src.web.routes.database.get_db_service") as mock_db_service:
            mock_session = AsyncMock()
            mock_db_service.return_value.get_session.return_value.__aenter__.return_value = (
                mock_session
            )

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

    @patch("src.web.routes.database.get_db_management_service")
    def test_get_stats_api(
        self, mock_get_service: MagicMock, client: TestClient
    ) -> None:
        """Test database statistics API endpoint."""
        # Arrange
        from src.api.services.db_management import DatabaseStats

        mock_service = MagicMock()
        mock_service.get_database_stats = AsyncMock(
            return_value=DatabaseStats(
                database_size_bytes=10485760,
                version="PostgreSQL 15.3",
                connection_count=5,
            )
        )
        mock_get_service.return_value = mock_service

        # Act
        response = client.get("/database/stats")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["database_size_bytes"] == 10485760
        assert "PostgreSQL" in data["version"]


class TestQueryHistoryIntegration:
    """Integration tests for query history functionality."""

    @patch("src.web.routes.database.get_db_service")
    def test_query_history_saved_after_execution(
        self, mock_get_db_service: MagicMock, client: TestClient
    ) -> None:
        """Test that query history is saved after query execution."""
        # Arrange
        from src.api.services.db_management import QueryResult

        mock_session = AsyncMock()
        mock_get_db_service.return_value.get_session.return_value.__aenter__.return_value = (
            mock_session
        )

        with patch("src.web.routes.database.get_db_management_service") as mock_get_mgmt:
            mock_mgmt_service = MagicMock()
            mock_mgmt_service.execute_query = AsyncMock(
                return_value=QueryResult(
                    success=True,
                    row_count=1,
                    columns=["id"],
                    rows=[[1]],
                    execution_time_ms=100.0,
                )
            )
            mock_get_mgmt.return_value = mock_mgmt_service

            # Act
            response = client.post(
                "/database/query",
                json={"sql": "SELECT 1", "confirmed": False},
            )

        # Assert
        assert response.status_code == 200
        # Verify session.execute was called (for saving history)
        assert mock_session.execute.called

    @patch("src.web.routes.database.get_db_service")
    def test_get_query_history_api(
        self, mock_get_db_service: MagicMock, client: TestClient
    ) -> None:
        """Test retrieving query history."""
        # Arrange
        from src.api.repositories.query_history_repository import QueryHistory

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_rows = [
            MagicMock(
                id=1,
                query_text="SELECT * FROM users",
                executed_at=datetime(2025, 1, 1, 12, 0, 0),
                execution_time_ms=150.5,
                status="success",
                row_count=10,
                error_message=None,
            )
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result
        mock_get_db_service.return_value.get_session.return_value.__aenter__.return_value = (
            mock_session
        )

        # Act
        response = client.get("/database/history?limit=10")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["query_text"] == "SELECT * FROM users"


class TestExportIntegration:
    """Integration tests for data export functionality."""

    @patch("src.web.routes.database.get_db_management_service")
    def test_export_csv(
        self, mock_get_service: MagicMock, client: TestClient
    ) -> None:
        """Test CSV export functionality."""
        # Arrange
        mock_service = MagicMock()
        mock_service.export_data = AsyncMock(
            return_value="id,name\n1,John\n2,Jane\n"
        )
        mock_get_service.return_value = mock_service

        # Act
        response = client.get(
            "/database/export?query=SELECT * FROM users&format=csv"
        )

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv"
        assert "id,name" in response.text

    @patch("src.web.routes.database.get_db_management_service")
    def test_export_json(
        self, mock_get_service: MagicMock, client: TestClient
    ) -> None:
        """Test JSON export functionality."""
        # Arrange
        mock_service = MagicMock()
        mock_service.export_data = AsyncMock(
            return_value='[{"id": 1, "name": "John"}]'
        )
        mock_get_service.return_value = mock_service

        # Act
        response = client.get(
            "/database/export?query=SELECT * FROM users&format=json"
        )

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert '"id"' in response.text or '"id":' in response.text

