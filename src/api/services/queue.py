"""RabbitMQ queue service client.

This module provides message queue operations using RabbitMQ with pika
for the API service.
"""

from __future__ import annotations

from typing import Optional

import pika
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection


class QueueService:
    """RabbitMQ queue service client.

    This class provides message queue operations using RabbitMQ.

    Attributes:
        url: RabbitMQ connection URL
    """

    def __init__(self, url: str) -> None:
        """Initialize queue service with connection URL.

        Args:
            url: RabbitMQ connection URL (e.g., amqp://user:pass@host:5672/)
        """
        self.url = url

    def get_connection(self) -> BlockingConnection:
        """Get a new RabbitMQ connection.

        Returns:
            RabbitMQ blocking connection instance
        """
        parameters = pika.URLParameters(self.url)
        return pika.BlockingConnection(parameters)

    def declare_queue(self, queue_name: str, durable: bool = True) -> None:
        """Declare a queue.

        Args:
            queue_name: Name of the queue to declare
            durable: Whether the queue should survive broker restart
        """
        connection = self.get_connection()
        try:
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, durable=durable)
        finally:
            connection.close()

    def publish_message(self, queue_name: str, message: str, persistent: bool = True) -> None:
        """Publish a message to a queue.

        Args:
            queue_name: Name of the queue
            message: Message content to send
            persistent: Whether message should survive broker restart
        """
        connection = self.get_connection()
        try:
            channel = connection.channel()
            properties = None
            if persistent:
                properties = pika.BasicProperties(delivery_mode=2)
            
            channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=message,
                properties=properties,
            )
        finally:
            connection.close()

    def consume_message(self, queue_name: str) -> Optional[str]:
        """Consume a single message from queue.

        Args:
            queue_name: Name of the queue

        Returns:
            Message content as string, or None if queue is empty
        """
        connection = self.get_connection()
        try:
            channel = connection.channel()
            method, properties, body = channel.basic_get(queue=queue_name, auto_ack=False)
            
            if method is None:
                return None
            
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return body.decode("utf-8")
        finally:
            connection.close()

    def purge_queue(self, queue_name: str) -> None:
        """Remove all messages from a queue.

        Args:
            queue_name: Name of the queue to purge
        """
        connection = self.get_connection()
        try:
            channel = connection.channel()
            channel.queue_purge(queue=queue_name)
        finally:
            connection.close()

    def health_check(self) -> bool:
        """Check if RabbitMQ connection is healthy.

        Returns:
            True if RabbitMQ is accessible, False otherwise
        """
        try:
            connection = self.get_connection()
            is_open = connection.is_open
            connection.close()
            return is_open
        except Exception:
            return False

