"""Health check routes for API service.

This module provides health check endpoints for monitoring service status
with caching and circuit breaker support.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request

from src.api.models.schemas import HealthResponse, ServiceHealthResponse
from src.api.resilience.circuit_breaker import (
    CircuitBreakerOpenError,
    get_circuit_breaker_manager,
)
from src.api.services.cache import get_cache
from src.api.services.container import ServiceContainer

router = APIRouter(prefix="", tags=["health"])


def get_container(request: Request) -> ServiceContainer:
    """Dependency to get service container from app state.

    Args:
        request: FastAPI request object

    Returns:
        Service container instance
    """
    return request.app.state.container


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns:
        Health status response
    """
    return HealthResponse(status="healthy", service="odin-api")


@router.get("/health/services", response_model=ServiceHealthResponse)
async def health_check_services(
    container: ServiceContainer = Depends(get_container),
) -> ServiceHealthResponse:
    """Check health of all dependent services with caching and circuit breaker.

    This endpoint uses the injected service container to check the health
    of all dependent services. Results are cached for 30 seconds to reduce
    load on services. Circuit breakers prevent cascading failures.

    Args:
        container: Service container with initialized services

    Returns:
        Health status of all services
    """
    cache = get_cache()
    cache_key = "health:services"

    # Try to get from cache first
    cached_result = await cache.get(cache_key)
    if cached_result:
        return ServiceHealthResponse(**cached_result)

    # Get circuit breaker manager
    cb_manager = get_circuit_breaker_manager()

    async def safe_health_check(name: str, check_func) -> bool:
        """Perform health check with circuit breaker.

        Args:
            name: Service name
            check_func: Health check function

        Returns:
            True if healthy, False if circuit open or unhealthy
        """
        try:
            breaker = await cb_manager.get_breaker(name, failure_threshold=3, timeout=30.0)
            return await breaker.call(check_func)
        except CircuitBreakerOpenError:
            # Circuit is open, service is known to be down
            return False
        except Exception:
            # Other errors also indicate unhealthy
            return False

    # Perform all health checks concurrently with circuit breakers
    db_task = safe_health_check("database", container.database.health_check)
    storage_task = safe_health_check("storage", container.storage.health_check)
    queue_task = safe_health_check("queue", container.queue.health_check)
    vault_task = safe_health_check("vault", container.vault.health_check)
    ollama_task = safe_health_check("ollama", container.ollama.health_check)

    # Wait for all health checks to complete
    db_healthy, storage_healthy, queue_healthy, vault_healthy, ollama_healthy = await asyncio.gather(
        db_task, storage_task, queue_task, vault_task, ollama_task
    )

    result = ServiceHealthResponse(
        database=db_healthy,
        storage=storage_healthy,
        queue=queue_healthy,
        vault=vault_healthy,
        ollama=ollama_healthy,
    )

    # Cache the result for 30 seconds
    await cache.set(cache_key, result.model_dump(), ttl=30.0)

    return result


@router.get("/health/circuit-breakers")
async def get_circuit_breaker_states() -> dict[str, str]:
    """Get the states of all circuit breakers.

    Returns:
        Dictionary mapping service name to circuit breaker state
    """
    cb_manager = get_circuit_breaker_manager()
    return cb_manager.get_states()

