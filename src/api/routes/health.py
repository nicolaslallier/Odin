"""Health check routes for API service.

This module provides health check endpoints for monitoring service status
with caching and circuit breaker support, including timeseries recording.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, status

from src.api.models.schemas import (
    HealthCheckBatchRequest,
    HealthCheckHistoryResponse,
    HealthCheckQueryParams,
    HealthCheckRecordResponse,
    HealthResponse,
    LatestHealthStatusResponse,
    ServiceHealthResponse,
)
from src.api.repositories.health_repository import HealthRepository
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


async def get_health_repository(
    container: ServiceContainer = Depends(get_container),
) -> HealthRepository:
    """Dependency to get health repository with database session.

    Args:
        container: Service container with database service

    Returns:
        HealthRepository instance with active session

    Yields:
        HealthRepository for use in endpoint
    """
    async with container.database.get_session() as session:
        yield HealthRepository(session=session)


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
    db_healthy, storage_healthy, queue_healthy, vault_healthy, ollama_healthy = (
        await asyncio.gather(db_task, storage_task, queue_task, vault_task, ollama_task)
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


@router.post(
    "/health/record", status_code=status.HTTP_201_CREATED, response_model=HealthCheckRecordResponse
)
async def record_health_checks(
    request: HealthCheckBatchRequest,
    repository: HealthRepository = Depends(get_health_repository),
) -> HealthCheckRecordResponse:
    """Record batch of health check data to TimescaleDB.

    This endpoint receives health check data from the worker and stores it
    in the TimescaleDB hypertable for historical analysis and monitoring.

    Args:
        request: Batch health check request with checks and optional timestamp
        repository: Health repository for database operations

    Returns:
        Response indicating number of records stored

    Example:
        >>> POST /health/record
        >>> {
        >>>   "checks": [
        >>>     {
        >>>       "service_name": "database",
        >>>       "service_type": "infrastructure",
        >>>       "is_healthy": true,
        >>>       "response_time_ms": 12.5
        >>>     }
        >>>   ]
        >>> }
    """
    # Use provided timestamp or current time
    if request.timestamp:
        timestamp = datetime.fromisoformat(request.timestamp.replace("Z", "+00:00"))
    else:
        timestamp = datetime.now(timezone.utc)

    # Insert health checks into database
    recorded_count = await repository.insert_health_checks(
        checks=request.checks, timestamp=timestamp
    )

    return HealthCheckRecordResponse(
        recorded=recorded_count,
        timestamp=timestamp.isoformat(),
        message="Health checks recorded successfully",
    )


@router.get("/health/history", response_model=HealthCheckHistoryResponse)
async def get_health_history(
    start_time: str = Query(..., description="Start time (ISO format)"),
    end_time: str = Query(..., description="End time (ISO format)"),
    service_names: list[str] | None = Query(None, description="Filter by service names"),
    service_type: str | None = Query(None, description="Filter by service type"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum records to return"),
    repository: HealthRepository = Depends(get_health_repository),
) -> HealthCheckHistoryResponse:
    """Query historical health check data from TimescaleDB.

    This endpoint retrieves historical health check records with optional
    filtering by service name, service type, and time range.

    Args:
        start_time: Start of time range (ISO format)
        end_time: End of time range (ISO format)
        service_names: Optional list of service names to filter
        service_type: Optional service type filter ('infrastructure' or 'application')
        limit: Maximum number of records to return
        repository: Health repository for database operations

    Returns:
        Historical health check records

    Example:
        >>> GET /health/history?start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z
    """
    # Build query parameters
    params = HealthCheckQueryParams(
        service_names=service_names,
        service_type=service_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    # Query health history from database
    records = await repository.query_health_history(params)

    return HealthCheckHistoryResponse(
        records=records,
        total=len(records),
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/health/latest", response_model=LatestHealthStatusResponse)
async def get_latest_health(
    repository: HealthRepository = Depends(get_health_repository),
) -> LatestHealthStatusResponse:
    """Get the latest health status for all services.

    This endpoint retrieves the most recent health check result for each
    service from the TimescaleDB hypertable.

    Args:
        repository: Health repository for database operations

    Returns:
        Latest health status for each service

    Example:
        >>> GET /health/latest
        >>> {
        >>>   "services": {
        >>>     "database": true,
        >>>     "api": true,
        >>>     "worker": false
        >>>   },
        >>>   "timestamp": "2024-01-15T10:30:00Z"
        >>> }
    """
    # Get latest health status from database
    services = await repository.get_latest_health_status()

    return LatestHealthStatusResponse(
        services=services,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
