"""Health check routes for API service.

This module provides health check endpoints for monitoring service status.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.config import APIConfig, get_config
from src.api.models.schemas import HealthResponse, ServiceHealthResponse
from src.api.services.database import DatabaseService
from src.api.services.ollama import OllamaService
from src.api.services.queue import QueueService
from src.api.services.storage import StorageService
from src.api.services.vault import VaultService

router = APIRouter(prefix="", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns:
        Health status response
    """
    return HealthResponse(status="healthy", service="odin-api")


@router.get("/health/services", response_model=ServiceHealthResponse)
async def health_check_services(config: APIConfig = Depends(get_config)) -> ServiceHealthResponse:
    """Check health of all dependent services.

    Args:
        config: API configuration

    Returns:
        Health status of all services
    """
    # Database health
    db_service = DatabaseService(dsn=config.postgres_dsn)
    db_healthy = await db_service.health_check()

    # Storage health
    storage_service = StorageService(
        endpoint=config.minio_endpoint,
        access_key=config.minio_access_key,
        secret_key=config.minio_secret_key,
        secure=config.minio_secure,
    )
    storage_healthy = storage_service.health_check()

    # Queue health
    queue_service = QueueService(url=config.rabbitmq_url)
    queue_healthy = queue_service.health_check()

    # Vault health
    vault_service = VaultService(addr=config.vault_addr, token=config.vault_token)
    vault_healthy = vault_service.health_check()

    # Ollama health
    ollama_service = OllamaService(base_url=config.ollama_base_url)
    ollama_healthy = await ollama_service.health_check()

    return ServiceHealthResponse(
        database=db_healthy,
        storage=storage_healthy,
        queue=queue_healthy,
        vault=vault_healthy,
        ollama=ollama_healthy,
    )


async def get_services_health() -> dict[str, bool]:
    """Helper function to get services health status.

    Returns:
        Dictionary with service names and their health status
    """
    config = get_config()
    response = await health_check_services(config)
    return {
        "database": response.database,
        "storage": response.storage,
        "queue": response.queue,
        "vault": response.vault,
        "ollama": response.ollama,
    }

