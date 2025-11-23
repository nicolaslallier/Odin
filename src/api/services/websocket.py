"""WebSocket manager service for real-time updates.

This module provides WebSocket connection management and broadcasting
capabilities for pushing real-time updates to connected portal clients.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket connection manager for real-time updates.

    This class manages WebSocket connections from portal clients and
    provides broadcasting capabilities for pushing statistics updates.

    Attributes:
        connections: Dictionary mapping client IDs to WebSocket connections
        space_subscriptions: Dictionary mapping space keys to sets of client IDs
    """

    def __init__(self) -> None:
        """Initialize WebSocket manager with empty connection pools."""
        self.connections: dict[str, WebSocket] = {}
        self.space_subscriptions: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str | None = None) -> str:
        """Accept and register a WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            client_id: Optional client identifier (generated if not provided)

        Returns:
            Client ID for the connection

        Raises:
            Exception: If connection acceptance fails
        """
        try:
            await websocket.accept()

            # Generate client ID if not provided
            if client_id is None:
                client_id = str(uuid4())

            async with self._lock:
                self.connections[client_id] = websocket

            logger.info(f"WebSocket client connected: {client_id}")
            return client_id

        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection: {e}")
            raise

    async def disconnect(self, client_id: str) -> None:
        """Disconnect and unregister a WebSocket connection.

        Args:
            client_id: Client identifier to disconnect
        """
        async with self._lock:
            # Remove from connections
            if client_id in self.connections:
                try:
                    await self.connections[client_id].close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket for {client_id}: {e}")
                del self.connections[client_id]

            # Remove from all space subscriptions
            for space_key in list(self.space_subscriptions.keys()):
                if client_id in self.space_subscriptions[space_key]:
                    self.space_subscriptions[space_key].remove(client_id)
                    # Clean up empty subscription sets
                    if not self.space_subscriptions[space_key]:
                        del self.space_subscriptions[space_key]

        logger.info(f"WebSocket client disconnected: {client_id}")

    async def subscribe_to_space(self, client_id: str, space_key: str) -> None:
        """Subscribe a client to updates for a specific space.

        Args:
            client_id: Client identifier
            space_key: Confluence space key to subscribe to
        """
        async with self._lock:
            if space_key not in self.space_subscriptions:
                self.space_subscriptions[space_key] = set()
            self.space_subscriptions[space_key].add(client_id)

        logger.debug(f"Client {client_id} subscribed to space {space_key}")

    async def unsubscribe_from_space(self, client_id: str, space_key: str) -> None:
        """Unsubscribe a client from updates for a specific space.

        Args:
            client_id: Client identifier
            space_key: Confluence space key to unsubscribe from
        """
        async with self._lock:
            if space_key in self.space_subscriptions:
                self.space_subscriptions[space_key].discard(client_id)
                # Clean up empty subscription sets
                if not self.space_subscriptions[space_key]:
                    del self.space_subscriptions[space_key]

        logger.debug(f"Client {client_id} unsubscribed from space {space_key}")

    async def broadcast_statistics(
        self,
        space_key: str,
        job_id: str,
        statistics: dict[str, Any],
        status: str = "completed",
    ) -> int:
        """Broadcast statistics update to subscribed clients.

        Args:
            space_key: Confluence space key
            job_id: Job identifier
            statistics: Statistics data to broadcast
            status: Job status (completed, failed)

        Returns:
            Number of clients that received the broadcast
        """
        message = {
            "type": "statistics_update",
            "space_key": space_key,
            "job_id": job_id,
            "status": status,
            "statistics": statistics,
        }

        # Get subscribed clients for this space
        subscribed_clients = self.space_subscriptions.get(space_key, set()).copy()

        # Send to subscribed clients
        sent_count = 0
        failed_clients = []

        for client_id in subscribed_clients:
            if client_id in self.connections:
                try:
                    await self.connections[client_id].send_json(message)
                    sent_count += 1
                except WebSocketDisconnect:
                    logger.warning(f"Client {client_id} disconnected during broadcast")
                    failed_clients.append(client_id)
                except Exception as e:
                    logger.error(f"Failed to send to client {client_id}: {e}")
                    failed_clients.append(client_id)

        # Clean up failed connections
        for client_id in failed_clients:
            await self.disconnect(client_id)

        logger.info(
            f"Broadcast statistics for {space_key} to {sent_count} clients "
            f"({len(failed_clients)} failed)"
        )

        return sent_count

    async def broadcast_to_all(self, message: dict[str, Any]) -> int:
        """Broadcast a message to all connected clients.

        Args:
            message: Message data to broadcast

        Returns:
            Number of clients that received the broadcast
        """
        sent_count = 0
        failed_clients = []

        # Get snapshot of current connections
        client_ids = list(self.connections.keys())

        for client_id in client_ids:
            if client_id in self.connections:
                try:
                    await self.connections[client_id].send_json(message)
                    sent_count += 1
                except WebSocketDisconnect:
                    logger.warning(f"Client {client_id} disconnected during broadcast")
                    failed_clients.append(client_id)
                except Exception as e:
                    logger.error(f"Failed to send to client {client_id}: {e}")
                    failed_clients.append(client_id)

        # Clean up failed connections
        for client_id in failed_clients:
            await self.disconnect(client_id)

        logger.info(f"Broadcast to all: {sent_count} clients ({len(failed_clients)} failed)")

        return sent_count

    async def send_to_client(self, client_id: str, message: dict[str, Any]) -> bool:
        """Send a message to a specific client.

        Args:
            client_id: Client identifier
            message: Message data to send

        Returns:
            True if sent successfully, False otherwise
        """
        if client_id not in self.connections:
            logger.warning(f"Client {client_id} not found for direct message")
            return False

        try:
            await self.connections[client_id].send_json(message)
            return True
        except WebSocketDisconnect:
            logger.warning(f"Client {client_id} disconnected during send")
            await self.disconnect(client_id)
            return False
        except Exception as e:
            logger.error(f"Failed to send to client {client_id}: {e}")
            await self.disconnect(client_id)
            return False

    async def handle_client_message(self, client_id: str, message: dict[str, Any]) -> None:
        """Handle incoming message from a client.

        Args:
            client_id: Client identifier
            message: Message data received from client
        """
        try:
            message_type = message.get("type")

            if message_type == "subscribe":
                space_key = message.get("space_key")
                if space_key:
                    await self.subscribe_to_space(client_id, space_key)
                    await self.send_to_client(
                        client_id,
                        {
                            "type": "subscribed",
                            "space_key": space_key,
                            "status": "success",
                        },
                    )

            elif message_type == "unsubscribe":
                space_key = message.get("space_key")
                if space_key:
                    await self.unsubscribe_from_space(client_id, space_key)
                    await self.send_to_client(
                        client_id,
                        {
                            "type": "unsubscribed",
                            "space_key": space_key,
                            "status": "success",
                        },
                    )

            elif message_type == "ping":
                await self.send_to_client(client_id, {"type": "pong"})

            else:
                logger.warning(f"Unknown message type from {client_id}: {message_type}")

        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
            await self.send_to_client(
                client_id,
                {"type": "error", "message": "Failed to process message"},
            )

    def get_connection_count(self) -> int:
        """Get the number of active connections.

        Returns:
            Number of connected clients
        """
        return len(self.connections)

    def get_subscription_count(self, space_key: str) -> int:
        """Get the number of clients subscribed to a space.

        Args:
            space_key: Confluence space key

        Returns:
            Number of subscribed clients
        """
        return len(self.space_subscriptions.get(space_key, set()))

    async def cleanup(self) -> None:
        """Cleanup all connections on shutdown."""
        logger.info("Cleaning up WebSocket connections...")

        client_ids = list(self.connections.keys())
        for client_id in client_ids:
            await self.disconnect(client_id)

        logger.info(f"Cleaned up {len(client_ids)} WebSocket connections")
