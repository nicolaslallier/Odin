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

    def test_ensure_connection_creates_connection(self, queue_service: QueueService) -> None:
        """Test that _ensure_connection creates a RabbitMQ connection."""
        with patch("src.api.services.queue.pika.BlockingConnection") as mock_conn:
            mock_connection = MagicMock()
            mock_connection.is_closed = False
            mock_conn.return_value = mock_connection

            connection = queue_service._ensure_connection()

            assert connection == mock_connection
            mock_conn.assert_called_once()

    def test_ensure_connection_amqp_error(self, queue_service: QueueService) -> None:
        with patch("src.api.services.queue.pika.BlockingConnection") as mock_conn:
            import pika

            mock_conn.side_effect = pika.exceptions.AMQPConnectionError("fail")
            with pytest.raises(Exception) as exc:
                queue_service._ensure_connection()
            assert "Failed to connect to RabbitMQ" in str(exc.value)

    def test_get_channel_raises_queue_error(self, queue_service: QueueService) -> None:
        with patch.object(queue_service, "_ensure_connection") as mock_ensure:
            mock_conn = MagicMock()
            mock_ensure.return_value = mock_conn
            # channel() will raise
            mock_conn.channel.side_effect = Exception("Broken")
            with pytest.raises(Exception) as exc, queue_service._get_channel():
                pass
            assert "Channel operation failed" in str(exc.value)

    def test_channel_close_error(self, queue_service: QueueService) -> None:
        with patch.object(queue_service, "_ensure_connection") as mock_ensure:
            mock_conn = MagicMock()
            mock_channel = MagicMock()
            mock_channel.is_open = True
            # channel.close itself raises
            mock_channel.close.side_effect = Exception("bad close")
            mock_conn.channel.return_value = mock_channel
            mock_ensure.return_value = mock_conn
            # Should NOT raise
            with queue_service._get_channel() as ch:
                pass

    def test_declare_queue_success(self, queue_service: QueueService) -> None:
        """Test declare_queue creates a queue."""
        with patch.object(queue_service, "_get_channel") as mock_get_channel:
            mock_channel = MagicMock()
            mock_get_channel.return_value.__enter__.return_value = mock_channel
            mock_get_channel.return_value.__exit__.return_value = None

            queue_service.declare_queue("test-queue")

            mock_channel.queue_declare.assert_called_once_with(queue="test-queue", durable=True)

    def test_declare_queue_error(self, queue_service: QueueService) -> None:
        with patch.object(queue_service, "_get_channel") as mock_get_channel:
            mock_channel = MagicMock()
            mock_channel.queue_declare.side_effect = Exception("fail declare")
            mock_get_channel.return_value.__enter__.return_value = mock_channel
            mock_get_channel.return_value.__exit__.return_value = None
            with pytest.raises(Exception) as exc:
                queue_service.declare_queue("test-queue")
            assert "fail declare" in str(exc.value)

    def test_publish_message_success(self, queue_service: QueueService) -> None:
        """Test publish_message sends a message to queue."""
        with patch.object(queue_service, "_get_channel") as mock_get_channel:
            mock_channel = MagicMock()
            mock_get_channel.return_value.__enter__.return_value = mock_channel
            mock_get_channel.return_value.__exit__.return_value = None

            queue_service.publish_message("test-queue", "test message")

            mock_channel.basic_publish.assert_called_once()
            call_args = mock_channel.basic_publish.call_args
            assert call_args[1]["exchange"] == ""
            assert call_args[1]["routing_key"] == "test-queue"
            assert call_args[1]["body"] == "test message"

    def test_publish_message_error(self, queue_service: QueueService) -> None:
        with patch.object(queue_service, "_get_channel") as mock_get_channel:
            mock_channel = MagicMock()
            mock_channel.basic_publish.side_effect = Exception("fail publish")
            mock_get_channel.return_value.__enter__.return_value = mock_channel
            mock_get_channel.return_value.__exit__.return_value = None
            with pytest.raises(Exception) as exc:
                queue_service.publish_message("tq", "msg")
            assert "fail publish" in str(exc.value)

    def test_consume_message_success(self, queue_service: QueueService) -> None:
        """Test consume_message receives a message from queue."""
        with patch.object(queue_service, "_get_channel") as mock_get_channel:
            mock_channel = MagicMock()
            mock_method = MagicMock()
            mock_method.delivery_tag = 1
            mock_properties = MagicMock()
            mock_body = b"test message"
            mock_channel.basic_get.return_value = (mock_method, mock_properties, mock_body)
            mock_get_channel.return_value.__enter__.return_value = mock_channel
            mock_get_channel.return_value.__exit__.return_value = None

            result = queue_service.consume_message("test-queue")

            assert result == "test message"
            mock_channel.basic_get.assert_called_once_with(queue="test-queue", auto_ack=False)
            mock_channel.basic_ack.assert_called_once_with(delivery_tag=1)

    def test_consume_message_error(self, queue_service: QueueService) -> None:
        with patch.object(queue_service, "_get_channel") as mock_get_channel:
            mock_channel = MagicMock()
            mock_channel.basic_get.side_effect = Exception("fail get")
            mock_get_channel.return_value.__enter__.return_value = mock_channel
            mock_get_channel.return_value.__exit__.return_value = None
            with pytest.raises(Exception) as exc:
                queue_service.consume_message("tq")
            assert "fail get" in str(exc.value)

    def test_consume_message_returns_none_when_empty(self, queue_service: QueueService) -> None:
        """Test consume_message returns None when queue is empty."""
        with patch.object(queue_service, "_get_channel") as mock_get_channel:
            mock_channel = MagicMock()
            mock_channel.basic_get.return_value = (None, None, None)
            mock_get_channel.return_value.__enter__.return_value = mock_channel
            mock_get_channel.return_value.__exit__.return_value = None

            result = queue_service.consume_message("test-queue")

            assert result is None

    def test_purge_queue_success(self, queue_service: QueueService) -> None:
        """Test purge_queue clears all messages from queue."""
        with patch.object(queue_service, "_get_channel") as mock_get_channel:
            mock_channel = MagicMock()
            mock_get_channel.return_value.__enter__.return_value = mock_channel
            mock_get_channel.return_value.__exit__.return_value = None

            queue_service.purge_queue("test-queue")

            mock_channel.queue_purge.assert_called_once_with(queue="test-queue")

    def test_purge_queue_error(self, queue_service: QueueService) -> None:
        with patch.object(queue_service, "_get_channel") as mock_get_channel:
            mock_channel = MagicMock()
            mock_channel.queue_purge.side_effect = Exception("fail purge")
            mock_get_channel.return_value.__enter__.return_value = mock_channel
            mock_get_channel.return_value.__exit__.return_value = None
            with pytest.raises(Exception) as exc:
                queue_service.purge_queue("tq")
            assert "fail purge" in str(exc.value)

    @pytest.mark.asyncio
    async def test_health_check_success(self, queue_service: QueueService) -> None:
        """Test health check returns True when RabbitMQ is accessible."""
        with patch.object(queue_service, "_ensure_connection") as mock_ensure_conn:
            mock_connection = MagicMock()
            mock_connection.is_open = True
            mock_ensure_conn.return_value = mock_connection

            result = await queue_service.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, queue_service: QueueService) -> None:
        """Test health check returns False when RabbitMQ is not accessible."""
        with patch.object(queue_service, "_ensure_connection") as mock_ensure_conn:
            mock_ensure_conn.side_effect = Exception("Connection failed")

            result = await queue_service.health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_close_handles_exception(self, queue_service: QueueService) -> None:
        # Simulate an exception when close() is called on connection
        with patch.object(queue_service, "_connection") as mock_conn:
            mock_conn.is_closed = False
            mock_conn.close.side_effect = Exception("fail close")
            # Should NOT raise
            await queue_service.close()
            # connection is set to None
            assert queue_service._connection is None
