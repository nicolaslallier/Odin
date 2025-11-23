"""Unit tests for health collection scheduled task.

This module tests the health collection task with mocked HTTP clients.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.worker.tasks.scheduled import collect_and_record_health_checks


class TestCollectAndRecordHealthChecks:
    """Tests for collect_and_record_health_checks task."""

    @patch("src.worker.tasks.scheduled.httpx.Client")
    def test_collect_health_checks_success(self, mock_client_class: MagicMock) -> None:
        """Test successful health check collection and recording.

        Args:
            mock_client_class: Mock httpx Client class
        """
        # Mock HTTP responses
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock infrastructure health response
        infra_response = MagicMock()
        infra_response.status_code = 200
        infra_response.json.return_value = {
            "database": True,
            "storage": True,
            "queue": True,
            "vault": True,
            "ollama": True,
        }

        # Mock API health response
        api_response = MagicMock()
        api_response.status_code = 200

        # Mock Flower response
        flower_response = MagicMock()
        flower_response.status_code = 200

        # Mock record response
        record_response = MagicMock()
        record_response.status_code = 201
        record_response.json.return_value = {"recorded": 10, "timestamp": "2024-01-15T10:00:00Z"}

        # Setup mock client to return different responses for different calls
        mock_client.get.side_effect = [
            infra_response,  # /health/services
            api_response,  # /health (API)
            flower_response,  # Flower workers
            flower_response,  # Flower dashboard
        ]
        mock_client.post.return_value = record_response

        # Execute task
        result = collect_and_record_health_checks()

        # Verify result
        assert result["status"] in ["success", "partial"]
        assert result["total_checks"] > 0
        assert "timestamp" in result
        assert "elapsed_seconds" in result

    @patch("src.worker.tasks.scheduled.httpx.Client")
    def test_collect_health_checks_api_unavailable(self, mock_client_class: MagicMock) -> None:
        """Test health collection when API is unavailable.

        Args:
            mock_client_class: Mock httpx Client class
        """
        # Mock HTTP responses with API failures
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock infrastructure health failure
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client.post.side_effect = Exception("Connection refused")

        # Execute task
        result = collect_and_record_health_checks()

        # Should handle errors gracefully
        assert result["status"] in ["error", "partial"]
        assert "errors" in result
        assert len(result["errors"]) > 0

    @patch("src.worker.tasks.scheduled.httpx.Client")
    def test_collect_health_checks_partial_failure(self, mock_client_class: MagicMock) -> None:
        """Test health collection with some services failing.

        Args:
            mock_client_class: Mock httpx Client class
        """
        # Mock HTTP responses with mixed results
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock infrastructure health response
        infra_response = MagicMock()
        infra_response.status_code = 200
        infra_response.json.return_value = {
            "database": True,
            "storage": False,  # Unhealthy
            "queue": True,
            "vault": True,
            "ollama": False,  # Unhealthy
        }

        # Mock API health response (success)
        api_response = MagicMock()
        api_response.status_code = 200

        # Mock Flower response (failure)
        flower_error = Exception("Flower unavailable")

        # Mock record response (success)
        record_response = MagicMock()
        record_response.status_code = 201
        record_response.json.return_value = {"recorded": 8, "timestamp": "2024-01-15T10:00:00Z"}

        # Setup mock client
        mock_client.get.side_effect = [
            infra_response,  # /health/services
            api_response,  # /health (API)
            flower_error,  # Flower workers (fail)
            Exception("timeout"),  # Flower dashboard (fail)
        ]
        mock_client.post.return_value = record_response

        # Execute task
        result = collect_and_record_health_checks()

        # Should record mixed results
        assert result["total_checks"] > 0
        assert result["healthy"] >= 0
        assert result["unhealthy"] >= 0
        assert result["healthy"] + result["unhealthy"] == result["total_checks"]

    @patch("src.worker.tasks.scheduled.httpx.Client")
    def test_collect_health_checks_record_failure(self, mock_client_class: MagicMock) -> None:
        """Test health collection when recording to API fails.

        Args:
            mock_client_class: Mock httpx Client class
        """
        # Mock HTTP responses
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock successful collection
        infra_response = MagicMock()
        infra_response.status_code = 200
        infra_response.json.return_value = {"database": True}

        api_response = MagicMock()
        api_response.status_code = 200

        flower_response = MagicMock()
        flower_response.status_code = 200

        # Mock record failure
        record_response = MagicMock()
        record_response.status_code = 500  # Server error

        mock_client.get.side_effect = [
            infra_response,
            api_response,
            flower_response,
            flower_response,
        ]
        mock_client.post.return_value = record_response

        # Execute task
        result = collect_and_record_health_checks()

        # Should report partial success
        assert result["status"] == "partial"
        assert "errors" in result
        assert any("Failed to record" in error for error in result["errors"])

    @patch("src.worker.tasks.scheduled.httpx.Client")
    def test_collect_health_checks_includes_response_times(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test that health checks include response time measurements.

        Args:
            mock_client_class: Mock httpx Client class
        """
        # Mock HTTP responses
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock responses
        infra_response = MagicMock()
        infra_response.status_code = 200
        infra_response.json.return_value = {"database": True}

        api_response = MagicMock()
        api_response.status_code = 200

        flower_response = MagicMock()
        flower_response.status_code = 200

        record_response = MagicMock()
        record_response.status_code = 201
        record_response.json.return_value = {"recorded": 5, "timestamp": "2024-01-15T10:00:00Z"}

        mock_client.get.side_effect = [
            infra_response,
            api_response,
            flower_response,
            flower_response,
        ]
        mock_client.post.return_value = record_response

        # Execute task
        result = collect_and_record_health_checks()

        # Should include timing information
        assert "elapsed_seconds" in result
        assert result["elapsed_seconds"] >= 0
