"""RabbitMQ queue service client.

This module provides message queue operations using RabbitMQ with pika
for the API service.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

import pika
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection

from src.api.exceptions import QueueError, ServiceUnavailableError


class QueueService:
    """RabbitMQ queue service client.

    This class provides message queue operations using RabbitMQ with
    connection pooling and proper resource management.

    Attributes:
        url: RabbitMQ connection URL
    """

    def __init__(self, url: str) -> None:
        """Initialize queue service with connection URL.

        Args:
            url: RabbitMQ connection URL (e.g., amqp://user:pass@host:5672/)
        """
        self.url = url
        self._connection: BlockingConnection | None = None
        self._parameters = pika.URLParameters(self.url)

    def _ensure_connection(self) -> BlockingConnection:
        """Ensure a valid connection exists.

        Returns:
            RabbitMQ connection instance

        Raises:
            ServiceUnavailableError: If connection cannot be established
        """
        try:
            if self._connection is None or self._connection.is_closed:
                self._connection = pika.BlockingConnection(self._parameters)
            return self._connection
        except pika.exceptions.AMQPConnectionError as e:
            raise ServiceUnavailableError(f"Failed to connect to RabbitMQ: {e}")

    @contextmanager
    def _get_channel(self) -> Generator[BlockingChannel, None, None]:
        """Get a channel with automatic cleanup.

        Yields:
            RabbitMQ channel instance

        Raises:
            QueueError: If channel creation fails
        """
        connection = self._ensure_connection()
        channel = None
        try:
            channel = connection.channel()
            yield channel
        except Exception as e:
            raise QueueError(f"Channel operation failed: {e}")
        finally:
            if channel and channel.is_open:
                try:
                    channel.close()
                except Exception:
                    pass

    async def close(self) -> None:
        """Close the connection and cleanup resources."""
        if self._connection and not self._connection.is_closed:
            try:
                self._connection.close()
            except Exception:
                pass
            finally:
                self._connection = None

    def declare_queue(self, queue_name: str, durable: bool = True) -> None:
        """Declare a queue.

        Args:
            queue_name: Name of the queue to declare
            durable: Whether the queue should survive broker restart

        Raises:
            QueueError: If queue declaration fails
        """
        with self._get_channel() as channel:
            channel.queue_declare(queue=queue_name, durable=durable)

    def publish_message(self, queue_name: str, message: str, persistent: bool = True) -> None:
        """Publish a message to a queue.

        Args:
            queue_name: Name of the queue
            message: Message content to send
            persistent: Whether message should survive broker restart

        Raises:
            QueueError: If message publishing fails
        """
        with self._get_channel() as channel:
            properties = None
            if persistent:
                properties = pika.BasicProperties(delivery_mode=2)

            channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=message,
                properties=properties,
            )

    def consume_message(self, queue_name: str) -> str | None:
        """Consume a single message from queue.

        Args:
            queue_name: Name of the queue

        Returns:
            Message content as string, or None if queue is empty

        Raises:
            QueueError: If message consumption fails
        """
        with self._get_channel() as channel:
            method, properties, body = channel.basic_get(queue=queue_name, auto_ack=False)

            if method is None:
                return None

            channel.basic_ack(delivery_tag=method.delivery_tag)
            return body.decode("utf-8")

    def purge_queue(self, queue_name: str) -> None:
        """Remove all messages from a queue.

        Args:
            queue_name: Name of the queue to purge

        Raises:
            QueueError: If queue purge fails
        """
        with self._get_channel() as channel:
            channel.queue_purge(queue=queue_name)

    async def health_check(self) -> bool:
        """Check if RabbitMQ connection is healthy.

        Returns:
            True if RabbitMQ is accessible, False otherwise
        """
        try:
            connection = self._ensure_connection()
            return connection.is_open
        except Exception:
            return False
