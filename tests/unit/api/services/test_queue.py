"""Unit tests for RabbitMQ queue service.

This module tests the queue service client for message operations,
queue management, and connection handling.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.api.services.queue import QueueService


class TestQueueService:
    """Test suite for QueueService."""

    @pytest.fixture
    def queue_service(self) -> QueueService:
        """Create a QueueService instance."""
        return QueueService(url="amqp://user:pass@localhost:5672/")

    def test_queue_service_initialization(self) -> None:
        """Test that QueueService initializes with URL."""
        service = QueueService(url="amqp://odin:password@rabbitmq:5672/")
        assert service.url == "amqp://odin:password@rabbitmq:5672/"

    def test_get_connection_creates_connection(self, queue_service: QueueService) -> None:
        """Test that get_connection creates a RabbitMQ connection."""
        with patch("src.api.services.queue.pika.BlockingConnection") as mock_conn:
            mock_connection = MagicMock()
            mock_conn.return_value = mock_connection
            
            connection = queue_service.get_connection()
            
            assert connection == mock_connection
            mock_conn.assert_called_once()

    def test_declare_queue_success(self, queue_service: QueueService) -> None:
        """Test declare_queue creates a queue."""
        with patch.object(queue_service, "get_connection") as mock_get_conn:
            mock_connection = MagicMock()
            mock_channel = MagicMock()
            mock_connection.channel.return_value = mock_channel
            mock_get_conn.return_value = mock_connection
            
            queue_service.declare_queue("test-queue")
            
            mock_channel.queue_declare.assert_called_once_with(
                queue="test-queue", durable=True
            )
            mock_connection.close.assert_called_once()

    def test_publish_message_success(self, queue_service: QueueService) -> None:
        """Test publish_message sends a message to queue."""
        with patch.object(queue_service, "get_connection") as mock_get_conn:
            mock_connection = MagicMock()
            mock_channel = MagicMock()
            mock_connection.channel.return_value = mock_channel
            mock_get_conn.return_value = mock_connection
            
            queue_service.publish_message("test-queue", "test message")
            
            mock_channel.basic_publish.assert_called_once()
            call_args = mock_channel.basic_publish.call_args
            assert call_args[1]["exchange"] == ""
            assert call_args[1]["routing_key"] == "test-queue"
            assert call_args[1]["body"] == "test message"
            mock_connection.close.assert_called_once()

    def test_consume_message_success(self, queue_service: QueueService) -> None:
        """Test consume_message receives a message from queue."""
        with patch.object(queue_service, "get_connection") as mock_get_conn:
            mock_connection = MagicMock()
            mock_channel = MagicMock()
            mock_method = MagicMock()
            mock_method.delivery_tag = 1
            mock_properties = MagicMock()
            mock_body = b"test message"
            mock_channel.basic_get.return_value = (mock_method, mock_properties, mock_body)
            mock_connection.channel.return_value = mock_channel
            mock_get_conn.return_value = mock_connection
            
            result = queue_service.consume_message("test-queue")
            
            assert result == "test message"
            mock_channel.basic_get.assert_called_once_with(queue="test-queue", auto_ack=False)
            mock_channel.basic_ack.assert_called_once_with(delivery_tag=1)
            mock_connection.close.assert_called_once()

    def test_consume_message_returns_none_when_empty(self, queue_service: QueueService) -> None:
        """Test consume_message returns None when queue is empty."""
        with patch.object(queue_service, "get_connection") as mock_get_conn:
            mock_connection = MagicMock()
            mock_channel = MagicMock()
            mock_channel.basic_get.return_value = (None, None, None)
            mock_connection.channel.return_value = mock_channel
            mock_get_conn.return_value = mock_connection
            
            result = queue_service.consume_message("test-queue")
            
            assert result is None
            mock_connection.close.assert_called_once()

    def test_purge_queue_success(self, queue_service: QueueService) -> None:
        """Test purge_queue clears all messages from queue."""
        with patch.object(queue_service, "get_connection") as mock_get_conn:
            mock_connection = MagicMock()
            mock_channel = MagicMock()
            mock_connection.channel.return_value = mock_channel
            mock_get_conn.return_value = mock_connection
            
            queue_service.purge_queue("test-queue")
            
            mock_channel.queue_purge.assert_called_once_with(queue="test-queue")
            mock_connection.close.assert_called_once()

    def test_health_check_success(self, queue_service: QueueService) -> None:
        """Test health check returns True when RabbitMQ is accessible."""
        with patch.object(queue_service, "get_connection") as mock_get_conn:
            mock_connection = MagicMock()
            mock_connection.is_open = True
            mock_get_conn.return_value = mock_connection
            
            result = queue_service.health_check()
            
            assert result is True
            mock_connection.close.assert_called_once()

    def test_health_check_failure(self, queue_service: QueueService) -> None:
        """Test health check returns False when RabbitMQ is not accessible."""
        with patch.object(queue_service, "get_connection") as mock_get_conn:
            mock_get_conn.side_effect = Exception("Connection failed")
            
            result = queue_service.health_check()
            
            assert result is False

