"""Service fixtures for testing.

This module provides pytest fixtures for mocking and testing services.
"""

from __future__ import annotations

from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from src.api.services.database import DatabaseService
from src.api.services.ollama import OllamaService
from src.api.services.queue import QueueService
from src.api.services.storage import StorageService
from src.api.services.vault import VaultService


@pytest.fixture
async def test_db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an in-memory SQLite database engine for testing.

    Yields:
        SQLite async engine for testing
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    # Create tables
    from src.api.repositories.data_repository import metadata
    
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session.

    Args:
        test_db_engine: Test database engine

    Yields:
        Test database session
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker
    
    async_session = async_sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session


@pytest.fixture
def mock_database_service() -> Mock:
    service = Mock(spec=DatabaseService)
    mock_cm = AsyncMock()
    mock_session = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session
    mock_cm.__aexit__.return_value = None
    service.get_session.return_value = mock_cm
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_storage_service() -> Mock:
    """Create a mock storage service.

    Returns:
        Mocked storage service
    """
    service = Mock(spec=StorageService)
    service.bucket_exists = Mock(return_value=True)
    service.create_bucket = Mock(return_value=None)
    service.upload_file = Mock(return_value=None)
    service.download_file = Mock(return_value=b"test content")
    service.delete_file = Mock(return_value=None)
    service.list_files = Mock(return_value=["file1.txt", "file2.txt"])
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_queue_service() -> Mock:
    """Create a mock queue service.

    Returns:
        Mocked queue service
    """
    service = Mock(spec=QueueService)
    service.declare_queue = Mock(return_value=None)
    service.publish_message = Mock(return_value=None)
    service.consume_message = Mock(return_value="test message")
    service.purge_queue = Mock(return_value=None)
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_vault_service() -> Mock:
    """Create a mock vault service.

    Returns:
        Mocked vault service
    """
    service = Mock(spec=VaultService)
    service.write_secret = Mock(return_value=None)
    service.read_secret = Mock(return_value={"key": "value"})
    service.delete_secret = Mock(return_value=None)
    service.list_secrets = Mock(return_value=["secret1", "secret2"])
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_ollama_service() -> Mock:
    """Create a mock Ollama service.

    Returns:
        Mocked Ollama service
    """
    service = Mock(spec=OllamaService)
    service.list_models = AsyncMock(return_value=[{"name": "test-model"}])
    service.generate_text = AsyncMock(return_value="Generated text")
    service.pull_model = AsyncMock(return_value=True)
    service.delete_model = AsyncMock(return_value=True)
    service.health_check = AsyncMock(return_value=True)
    service.initialize = AsyncMock(return_value=None)
    service.close = AsyncMock(return_value=None)
    return service


@pytest.fixture
def mock_service_container(
    mock_database_service: Mock,
    mock_storage_service: Mock,
    mock_queue_service: Mock,
    mock_vault_service: Mock,
    mock_ollama_service: Mock,
) -> Mock:
    """Create a mock service container with all services.

    Args:
        mock_database_service: Mocked database service
        mock_storage_service: Mocked storage service
        mock_queue_service: Mocked queue service
        mock_vault_service: Mocked vault service
        mock_ollama_service: Mocked Ollama service

    Returns:
        Mocked service container
    """
    container = Mock()
    container.database = mock_database_service
    container.storage = mock_storage_service
    container.queue = mock_queue_service
    container.vault = mock_vault_service
    container.ollama = mock_ollama_service
    container.initialize = AsyncMock(return_value=None)
    container.shutdown = AsyncMock(return_value=None)
    return container

