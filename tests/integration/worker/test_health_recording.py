"""Integration tests for worker health recording to API.

This module tests the worker-to-API integration for health check recording.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import httpx

from src.worker.tasks.scheduled import collect_and_record_health_checks


@pytest.mark.integration
class TestWorkerHealthRecording:
    """Integration tests for worker health recording."""

    @patch("src.worker.tasks.scheduled.httpx.Client")
    def test_end_to_end_health_recording(self, mock_client_class: MagicMock) -> None:
        """Test complete flow from collection to recording.

        Args:
            mock_client_class: Mock httpx Client class
        """
        # Setup mock responses that simulate real service behavior
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Simulate infrastructure health check
        infra_response = MagicMock()
        infra_response.status_code = 200
        infra_response.json.return_value = {
            "database": True,
            "storage": True,
            "queue": True,
            "vault": True,
            "ollama": True,
        }

        # Simulate API health check
        api_response = MagicMock()
        api_response.status_code = 200

        # Simulate Flower health check
        flower_response = MagicMock()
        flower_response.status_code = 200

        # Simulate successful recording
        record_response = MagicMock()
        record_response.status_code = 201
        record_response.json.return_value = {
            "recorded": 10,
            "timestamp": "2024-01-15T10:00:00Z",
            "message": "Health checks recorded successfully",
        }

        # Configure mock to return appropriate responses
        mock_client.get.side_effect = [
            infra_response,  # Infrastructure health
            api_response,  # API health
            flower_response,  # Worker status
            flower_response,  # Flower dashboard
        ]
        mock_client.post.return_value = record_response

        # Execute the task
        result = collect_and_record_health_checks()

        # Verify the task completed successfully
        assert result["status"] == "success"
        assert result["total_checks"] == 10
        assert result["recorded"] == 10
        assert result["errors"] == []

        # Verify POST to /health/record was called
        assert mock_client.post.called
        post_call = mock_client.post.call_args
        assert "/health/record" in post_call[0][0]

        # Verify the payload structure
        payload = post_call[1]["json"]
        assert "checks" in payload
        assert "timestamp" in payload
        assert len(payload["checks"]) == 10

    @patch("src.worker.tasks.scheduled.httpx.Client")
    def test_worker_handles_api_recording_failure(self, mock_client_class: MagicMock) -> None:
        """Test worker handles API recording failures gracefully.

        Args:
            mock_client_class: Mock httpx Client class
        """
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Setup successful collection
        infra_response = MagicMock()
        infra_response.status_code = 200
        infra_response.json.return_value = {"database": True}

        api_response = MagicMock()
        api_response.status_code = 200

        flower_response = MagicMock()
        flower_response.status_code = 200

        # Simulate recording failure
        record_response = MagicMock()
        record_response.status_code = 500  # Internal server error

        mock_client.get.side_effect = [
            infra_response,
            api_response,
            flower_response,
            flower_response,
        ]
        mock_client.post.return_value = record_response

        # Execute the task
        result = collect_and_record_health_checks()

        # Should report partial success
        assert result["status"] == "partial"
        assert result["total_checks"] > 0
        assert len(result["errors"]) > 0
        assert any("Failed to record" in error for error in result["errors"])

    @patch("src.worker.tasks.scheduled.httpx.Client")
    def test_worker_continues_on_collection_errors(self, mock_client_class: MagicMock) -> None:
        """Test worker continues collecting even if some services fail.

        Args:
            mock_client_class: Mock httpx Client class
        """
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Simulate mixed success/failure
        infra_response = MagicMock()
        infra_response.status_code = 200
        infra_response.json.return_value = {"database": True}

        # API check fails
        api_error = httpx.ConnectError("Connection refused")

        # Flower check succeeds
        flower_response = MagicMock()
        flower_response.status_code = 200

        # Recording succeeds
        record_response = MagicMock()
        record_response.status_code = 201
        record_response.json.return_value = {"recorded": 5, "timestamp": "2024-01-15T10:00:00Z"}

        mock_client.get.side_effect = [
            infra_response,
            api_error,  # API fails
            flower_response,
            flower_response,
        ]
        mock_client.post.return_value = record_response

        # Execute the task
        result = collect_and_record_health_checks()

        # Should still record available data
        assert result["total_checks"] > 0
        assert result["recorded"] > 0
        # Should have recorded infrastructure + flower checks despite API failure
        assert result["unhealthy"] > 0  # API marked as unhealthy
