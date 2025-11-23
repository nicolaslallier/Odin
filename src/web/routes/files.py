"""File manager page routes.

This module contains route handlers for the file manager page, following the
Single Responsibility Principle (SRP) from SOLID.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Create router
router = APIRouter(tags=["files"])

# Configure templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/files", response_class=HTMLResponse)
async def files_page(request: Request) -> HTMLResponse:
    """Render the file manager page.

    This endpoint serves the MinIO file management interface,
    allowing users to upload, download, delete, and preview files.

    Args:
        request: The incoming HTTP request

    Returns:
        HTMLResponse with the rendered file manager page template

    Example:
        When accessed via browser, displays the file manager interface
        with upload form, file list, and preview capabilities.
    """
    context = {
        "title": "File Manager",
        "active_menu": "files",
        "default_bucket": "odin-files",
    }
    return templates.TemplateResponse(request, "files.html", context)
