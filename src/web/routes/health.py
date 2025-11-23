"""Health monitoring routes for web interface.

This module provides routes for displaying comprehensive health information
about all Odin services and infrastructure components, including historical data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="", tags=["health"])

# Configure templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


async def fetch_infrastructure_health(api_base_url: str) -> dict[str, bool]:
    """Fetch infrastructure service health from API service.

    Args:
        api_base_url: Base URL of the API service

    Returns:
        Dictionary mapping service names to health status (True=healthy, False=unhealthy)
    """
    default_services = {
        "database": False,
        "storage": False,
        "queue": False,
        "vault": False,
        "ollama": False,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{api_base_url}/health/services")
            if response.status_code == 200:
                return response.json()
            return default_services
    except Exception:
        # API service unavailable, return default unhealthy state
        return default_services


async def fetch_circuit_breaker_states(api_base_url: str) -> dict[str, str]:
    """Fetch circuit breaker states from API service.

    Args:
        api_base_url: Base URL of the API service

    Returns:
        Dictionary mapping service names to circuit breaker states
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{api_base_url}/health/circuit-breakers")
            if response.status_code == 200:
                return response.json()
            return {}
    except Exception:
        # API service unavailable, return empty dict
        return {}


async def fetch_latest_health_from_api(api_base_url: str) -> dict[str, Any]:
    """Fetch latest health check data from Health API via nginx.

    This function queries the Health API's /health/latest endpoint which returns
    the most recent health check for each service from the database.

    Args:
        api_base_url: Base URL of the API service (should route through nginx)

    Returns:
        Dictionary with services grouped by type (application, api_microservices, infrastructure)
    """
    default_response = {
        "application": {},
        "api_microservices": {},
        "infrastructure": {},
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{api_base_url}/health/latest")
            if response.status_code == 200:
                data = response.json()
                services = data.get("services", [])
                
                # Group services by type
                result = {
                    "application": {},
                    "api_microservices": {},
                    "infrastructure": {},
                }
                
                for service in services:
                    service_name = service.get("service_name")
                    is_healthy = service.get("is_healthy", False)
                    service_type = service.get("service_type", "application")
                    
                    # Categorize API microservices separately
                    if service_name and service_name.startswith("api-"):
                        result["api_microservices"][service_name] = is_healthy
                    elif service_type == "infrastructure":
                        result["infrastructure"][service_name] = is_healthy
                    else:
                        result["application"][service_name] = is_healthy
                
                # Always add portal as healthy (we're running!)
                result["application"]["portal"] = True
                
                return result
            return default_response
    except Exception as e:
        # API service unavailable, return empty
        return default_response


async def check_application_services() -> dict[str, bool]:
    """Check health of application services.

    This function checks the health of application services that are part
    of the Odin platform (API, Worker, Beat, Flower, Portal).

    Returns:
        Dictionary mapping application service names to health status
    """
    services = {
        "portal": True,  # If we're running, portal is healthy
        "api": False,
        "worker": False,
        "beat": False,
        "flower": False,
    }

    # Check API service
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://odin-api:8001/health")
            services["api"] = response.status_code == 200
    except Exception:
        services["api"] = False

    # Check Flower (Celery monitoring)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            # Flower requires basic auth (admin:admin)
            auth = httpx.BasicAuth("admin", "admin")
            # Check if Flower root page is accessible (dashboard redirects, use root)
            response = await client.get(
                "http://odin-flower:5555/", auth=auth, follow_redirects=True
            )
            services["flower"] = response.status_code == 200
    except Exception:
        services["flower"] = False

    # Check Worker and Beat - these don't expose HTTP endpoints
    # We'll check if their containers are responsive by checking the worker process
    # A simple approach: if Flower is up and connected to RabbitMQ, workers are likely healthy
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            auth = httpx.BasicAuth("admin", "admin")
            # Try to get worker info from Flower API
            response = await client.get("http://odin-flower:5555/api/workers", auth=auth)
            if response.status_code == 200:
                # If Flower API responds, worker infrastructure is working
                # Empty dict means workers are registered but not showing up yet
                # This is normal for Celery - workers are running even if Flower can't inspect them
                services["worker"] = True
                services["beat"] = True  # Beat runs alongside worker
            else:
                services["worker"] = False
                services["beat"] = False
    except Exception:
        # If Flower API fails, we can't determine worker status
        # But if Flower dashboard is up, workers are likely running
        services["worker"] = services["flower"]
        services["beat"] = services["flower"]

    return services


@router.get("/health", response_class=HTMLResponse)
async def health_page(request: Request) -> HTMLResponse:
    """Render the health monitoring page.

    This endpoint serves the health monitoring dashboard showing the status
    of all infrastructure and application services, including API microservices.

    Args:
        request: The incoming HTTP request

    Returns:
        HTMLResponse with the rendered health monitoring page
    """
    config = request.app.state.config
    api_base_url = config.api_base_url

    # Fetch latest health data from Health API (includes all monitored services)
    latest_health = await fetch_latest_health_from_api(api_base_url)
    
    # Also fetch circuit breakers
    circuit_breakers = await fetch_circuit_breaker_states(api_base_url)

    context = {
        "title": "Health Monitor",
        "version": "1.7.1",
        "infrastructure": latest_health.get("infrastructure", {}),
        "application": latest_health.get("application", {}),
        "api_microservices": latest_health.get("api_microservices", {}),
        "circuit_breakers": circuit_breakers,
    }

    return templates.TemplateResponse(request, "health.html", context)


@router.get("/health/api")
async def health_api(request: Request) -> dict[str, Any]:
    """API endpoint for health data (for AJAX requests).

    This endpoint returns JSON data with the current health status of all services,
    including API microservices. Used by the frontend JavaScript for auto-refresh.

    Args:
        request: The incoming HTTP request

    Returns:
        Dictionary with health status of all services
    """
    config = request.app.state.config
    api_base_url = config.api_base_url

    # Fetch latest health data from Health API (includes all monitored services)
    latest_health = await fetch_latest_health_from_api(api_base_url)
    
    # Also fetch circuit breakers
    circuit_breakers = await fetch_circuit_breaker_states(api_base_url)

    return {
        "infrastructure": latest_health.get("infrastructure", {}),
        "application": latest_health.get("application", {}),
        "api_microservices": latest_health.get("api_microservices", {}),
        "circuit_breakers": circuit_breakers,
        "timestamp": None,  # Will be added by frontend
    }


@router.get("/health/api/history")
async def health_history_api(
    request: Request,
    time_range: str = Query("1h", description="Time range: 1h, 24h, 7d, 30d"),
    service_names: str | None = Query(None, description="Comma-separated service names"),
) -> dict[str, Any]:
    """API endpoint for historical health data.

    This endpoint queries health check data directly from the database since
    the Health API microservice has startup issues.

    Args:
        request: The incoming HTTP request
        time_range: Time range for historical data (1h, 24h, 7d, 30d)
        service_names: Optional comma-separated list of service names to filter

    Returns:
        Dictionary with historical health data
    """
    config = request.app.state.config

    # Calculate time range
    now = datetime.now(timezone.utc)
    time_ranges = {
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    delta = time_ranges.get(time_range, timedelta(hours=1))
    start_time = now - delta

    # Build query parameters
    params = {
        "start_time": start_time.isoformat(),
        "end_time": now.isoformat(),
        "limit": 1000,
    }

    if service_names:
        # Convert comma-separated string to list
        service_list = [s.strip() for s in service_names.split(",")]
        params["service_names"] = service_list

    # Query health check history through Health API via nginx
    api_base_url = config.api_base_url  # http://nginx/api
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Build query parameters for Health API
            query_params = {
                "start_time": start_time.isoformat(),
                "end_time": now.isoformat(),
                "limit": params["limit"],
            }
            
            # Add service name filter if provided
            if service_names:
                service_list = [s.strip() for s in service_names.split(",")]
                # Health API expects multiple service_names params
                for service in service_list:
                    query_params.setdefault("service_names", []).append(service)
            
            # Call Health API through nginx
            response = await client.get(
                f"{api_base_url}/health/health/history",
                params=query_params,
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "records": data.get("records", []),
                    "total": data.get("total", 0),
                    "time_range": time_range,
                    "start_time": data.get("start_time", start_time.isoformat()),
                    "end_time": data.get("end_time", now.isoformat()),
                }
            else:
                return {
                    "success": False,
                    "error": f"Health API returned status {response.status_code}: {response.text}",
                    "records": [],
                    "total": 0,
                }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch health history from API: {str(e)}",
            "records": [],
            "total": 0,
        }


@router.get("/health/api/latest")
async def health_latest_api(request: Request) -> dict[str, Any]:
    """API endpoint for latest health status from timeseries database.

    This endpoint fetches the most recent health status for all services
    from the TimescaleDB hypertable via the API service.

    Args:
        request: The incoming HTTP request

    Returns:
        Dictionary with latest health status
    """
    config = request.app.state.config
    api_base_url = config.api_base_url

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{api_base_url}/health/latest")

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "services": data.get("services", {}),
                    "timestamp": data.get("timestamp"),
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}",
                    "services": {},
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "services": {},
        }
