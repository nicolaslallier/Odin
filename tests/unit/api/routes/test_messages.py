"""Unit tests for message queue routes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.config import APIConfig
from src.api.routes.messages import router


class TestMessageRoutes:
    """Test suite for message routes."""

    @pytest.fixture
    def mock_config(self) -> APIConfig:
        """Create a mock configuration."""
        return APIConfig(
            host="0.0.0.0",
            port=8001,
            postgres_dsn="postgresql://test:test@localhost:5432/test",
            minio_endpoint="minio:9000",
            minio_access_key="minioadmin",
            minio_secret_key="minioadmin",
            rabbitmq_url="amqp://test:test@localhost:5672/",
            vault_addr="http://vault:8200",
            vault_token="test-token",
            ollama_base_url="http://ollama:11434",
        )

    @pytest.fixture
    def app(self, mock_config: APIConfig) -> FastAPI:
        """Create a test FastAPI app."""
        app = FastAPI()
        app.state.config = mock_config
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    def test_send_message_success(self, client: TestClient, app: FastAPI) -> None:
        """Test sending a message to queue."""
        from src.api.routes.messages import get_queue_service

        mock_queue = MagicMock()
        mock_queue.publish_message = MagicMock()

        app.dependency_overrides[get_queue_service] = lambda: mock_queue

        try:
            response = client.post(
                "/messages/send",
                json={"queue": "test-queue", "message": "Hello, World!"},
            )

            assert response.status_code == 200
            assert "sent" in response.json()["message"].lower()
            mock_queue.publish_message.assert_called_once_with("test-queue", "Hello, World!")
        finally:
            app.dependency_overrides.clear()

    def test_send_message_error(self, client: TestClient, app: FastAPI) -> None:
        """Test sending a message with error."""
        from src.api.exceptions import QueueError
        from src.api.routes.messages import get_queue_service

        mock_queue = MagicMock()
        mock_queue.publish_message = MagicMock(side_effect=QueueError("Queue error"))

        app.dependency_overrides[get_queue_service] = lambda: mock_queue

        try:
            response = client.post(
                "/messages/send",
                json={"queue": "test-queue", "message": "Hello, World!"},
            )

            assert response.status_code == 500
            assert "Queue error" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_receive_message_success(self, client: TestClient, app: FastAPI) -> None:
        """Test receiving a message from queue."""
        from src.api.routes.messages import get_queue_service

        mock_queue = MagicMock()
        mock_queue.consume_message = MagicMock(return_value="Test message")

        app.dependency_overrides[get_queue_service] = lambda: mock_queue

        try:
            response = client.get("/messages/receive?queue_name=test-queue")

            assert response.status_code == 200
            assert response.json()["queue"] == "test-queue"
            assert response.json()["message"] == "Test message"
            mock_queue.consume_message.assert_called_once_with("test-queue")
        finally:
            app.dependency_overrides.clear()

    def test_receive_message_empty_queue(self, client: TestClient, app: FastAPI) -> None:
        """Test receiving from empty queue."""
        from src.api.routes.messages import get_queue_service

        mock_queue = MagicMock()
        mock_queue.consume_message = MagicMock(return_value=None)

        app.dependency_overrides[get_queue_service] = lambda: mock_queue

        try:
            response = client.get("/messages/receive?queue_name=test-queue")

            assert response.status_code == 200
            assert response.json()["queue"] == "test-queue"
            assert response.json()["message"] is None
        finally:
            app.dependency_overrides.clear()

    def test_receive_message_error(self, client: TestClient, app: FastAPI) -> None:
        """Test receiving a message with error."""
        from src.api.exceptions import QueueError
        from src.api.routes.messages import get_queue_service

        mock_queue = MagicMock()
        mock_queue.consume_message = MagicMock(side_effect=QueueError("Queue error"))

        app.dependency_overrides[get_queue_service] = lambda: mock_queue

        try:
            response = client.get("/messages/receive?queue_name=test-queue")

            assert response.status_code == 500
            assert "Queue error" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
