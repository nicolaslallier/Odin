"""Log viewer route for web interface.

This module provides the route to render the log viewer page and proxy API requests.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_class=HTMLResponse)
async def logs_page(request: Request) -> HTMLResponse:
    """Render the log viewer page.

    Args:
        request: FastAPI request object

    Returns:
        Rendered HTML response

    Example:
        GET /logs
        GET /logs?level=ERROR
        GET /logs?service=api&start_time=2024-01-01T00:00:00Z
    """
    templates = request.app.state.templates
    config = request.app.state.config

    # Get query parameters for deep linking
    level = request.query_params.get("level")
    service = request.query_params.get("service")
    start_time = request.query_params.get("start_time")
    end_time = request.query_params.get("end_time")
    search = request.query_params.get("search")

    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "api_base_url": "/logs/proxy",  # Use proxy without /api suffix
            "initial_level": level,
            "initial_service": service,
            "initial_start_time": start_time,
            "initial_end_time": end_time,
            "initial_search": search,
        },
    )


@router.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def api_proxy(path: str, request: Request) -> Response:
    """Proxy API requests to the internal API service.

    This endpoint proxies requests from the browser to the internal API service,
    avoiding CORS issues and exposing the internal API.

    Args:
        path: API path to proxy (e.g., "api/v1/logs")
        request: FastAPI request object

    Returns:
        Proxied response from API service
    """
    config = request.app.state.config
    
    # Build target URL - path already includes /api/v1/logs
    target_url = f"{config.api_base_url}/{path}"
    
    # Forward query parameters
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"
    
    # Forward request to API
    async with httpx.AsyncClient() as client:
        try:
            if request.method == "GET":
                response = await client.get(target_url, timeout=30.0)
            elif request.method == "POST":
                body = await request.body()
                response = await client.post(
                    target_url,
                    content=body,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0,
                )
            else:
                return JSONResponse(
                    {"error": f"Method {request.method} not supported"},
                    status_code=405,
                )
            
            # Return proxied response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
        except httpx.RequestError as e:
            return JSONResponse(
                {"error": f"Failed to connect to API: {str(e)}"},
                status_code=502,
            )
        except Exception as e:
            return JSONResponse(
                {"error": f"Proxy error: {str(e)}"},
                status_code=500,
            )

