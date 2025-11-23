from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["image-analyzer"])

templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/image-analyzer", response_class=HTMLResponse)
async def image_analyzer_page(request: Request) -> HTMLResponse:
    """Render the Image Analyzer page."""
    context = {
        "title": "Image Analyzer",
        "active_menu": "image-analyzer",
    }
    return templates.TemplateResponse(request, "image_analyzer.html", context)
