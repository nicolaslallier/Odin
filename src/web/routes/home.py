"""Home page routes.

This module contains route handlers for the home page, following the
Single Responsibility Principle (SRP) from SOLID.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# Create router
router = APIRouter(tags=["home"])

# Configure templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/ping")
async def health_ping() -> JSONResponse:
    """Simple health check endpoint.

    Returns:
        JSON response with healthy status
    """
    return JSONResponse({"status": "healthy"})


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render the home page.

    This endpoint serves the main landing page of the application,
    displaying a "Hello World" message.

    Args:
        request: The incoming HTTP request

    Returns:
        HTMLResponse with the rendered home page template

    Example:
        When accessed via browser, displays the home page with
        "Hello World" message and Odin branding.
    """
    context = {
        "title": "Welcome to Odin",
        "message": "Hello World",
        "version": "1.6.0",
    }
    return templates.TemplateResponse(request, "index.html", context)
