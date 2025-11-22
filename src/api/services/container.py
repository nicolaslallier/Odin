"""Service container for dependency injection.

This module provides a service container that manages the lifecycle of all
services, following the Dependency Inversion Principle (DIP) from SOLID.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from src.api.config import APIConfig
from src.api.services.database import DatabaseService
from src.api.services.image_analysis import ImageAnalysisService
from src.api.services.ollama import OllamaService
from src.api.services.queue import QueueService
from src.api.services.storage import StorageService
from src.api.services.vault import VaultService


class ServiceContainer:
    """Container for managing service instances and their lifecycle.

    This class implements the Service Locator pattern and manages the lifecycle
    of all external service connections. It ensures services are initialized
    once and reused across requests.

    Attributes:
        config: API configuration
        database: Database service instance
        storage: Storage service instance
        queue: Queue service instance
        vault: Vault service instance
        ollama: LLM service instance
        image_analysis: Image analysis service instance
    """

    def __init__(self, config: APIConfig) -> None:
        """Initialize the service container.

        Args:
            config: API configuration containing connection details
        """
        self.config = config
        self._database: Optional[DatabaseService] = None
        self._storage: Optional[StorageService] = None
        self._queue: Optional[QueueService] = None
        self._vault: Optional[VaultService] = None
        self._ollama: Optional[OllamaService] = None
        self._image_analysis: Optional[ImageAnalysisService] = None

    async def initialize(self) -> None:
        """Initialize all services.

        This method creates service instances and establishes connections.
        It should be called during application startup.
        """
        # Initialize database service
        self._database = DatabaseService(dsn=self.config.async_postgres_dsn)

        # Initialize storage service
        self._storage = StorageService(
            endpoint=self.config.minio_endpoint,
            access_key=self.config.minio_access_key,
            secret_key=self.config.minio_secret_key,
            secure=self.config.minio_secure,
        )

        # Initialize queue service
        self._queue = QueueService(url=self.config.rabbitmq_url)

        # Initialize vault service
        self._vault = VaultService(addr=self.config.vault_addr, token=self.config.vault_token)

        # Initialize Ollama service
        self._ollama = OllamaService(base_url=self.config.ollama_base_url)
        await self._ollama.initialize()

        # Initialize Image Analysis service
        self._image_analysis = ImageAnalysisService(
            storage=self._storage,
            database=self._database,
            ollama=self._ollama,
            default_model=self.config.vision_model_default,
            image_bucket=self.config.image_bucket,
            max_size_mb=self.config.max_image_size_mb,
        )

    async def shutdown(self) -> None:
        """Shutdown all services and cleanup resources.

        This method closes all connections and releases resources.
        It should be called during application shutdown.
        """
        if self._database:
            await self._database.close()

        if self._ollama:
            await self._ollama.close()

        if self._queue:
            await self._queue.close()

    @property
    def database(self) -> DatabaseService:
        """Get the database service instance.

        Returns:
            Database service instance

        Raises:
            RuntimeError: If container not initialized
        """
        if self._database is None:
            raise RuntimeError("ServiceContainer not initialized. Call initialize() first.")
        return self._database

    @property
    def storage(self) -> StorageService:
        """Get the storage service instance.

        Returns:
            Storage service instance

        Raises:
            RuntimeError: If container not initialized
        """
        if self._storage is None:
            raise RuntimeError("ServiceContainer not initialized. Call initialize() first.")
        return self._storage

    @property
    def queue(self) -> QueueService:
        """Get the queue service instance.

        Returns:
            Queue service instance

        Raises:
            RuntimeError: If container not initialized
        """
        if self._queue is None:
            raise RuntimeError("ServiceContainer not initialized. Call initialize() first.")
        return self._queue

    @property
    def vault(self) -> VaultService:
        """Get the vault service instance.

        Returns:
            Vault service instance

        Raises:
            RuntimeError: If container not initialized
        """
        if self._vault is None:
            raise RuntimeError("ServiceContainer not initialized. Call initialize() first.")
        return self._vault

    @property
    def ollama(self) -> OllamaService:
        """Get the Ollama service instance.

        Returns:
            Ollama service instance

        Raises:
            RuntimeError: If container not initialized
        """
        if self._ollama is None:
            raise RuntimeError("ServiceContainer not initialized. Call initialize() first.")
        return self._ollama

    @property
    def image_analysis(self) -> ImageAnalysisService:
        """Get the image analysis service instance.

        Returns:
            Image analysis service instance

        Raises:
            RuntimeError: If container not initialized
        """
        if self._image_analysis is None:
            raise RuntimeError("ServiceContainer not initialized. Call initialize() first.")
        return self._image_analysis


@asynccontextmanager
async def get_service_container(config: APIConfig) -> AsyncGenerator[ServiceContainer, None]:
    """Context manager for service container lifecycle.

    This function manages the full lifecycle of the service container,
    ensuring proper initialization and cleanup.

    Args:
        config: API configuration

    Yields:
        Initialized service container

    Example:
        >>> async with get_service_container(config) as container:
        >>>     db = container.database
        >>>     result = await db.health_check()
    """
    container = ServiceContainer(config)
    await container.initialize()
    try:
        yield container
    finally:
        await container.shutdown()

