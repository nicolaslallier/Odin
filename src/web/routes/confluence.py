"""Confluence integration routes for web portal.

This module contains route handlers for the Confluence integration interface.
The web portal acts as a thin client that only communicates with the Odin API.
It never directly contacts Confluence - all operations go through the API layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

# Create router
router = APIRouter(tags=["confluence"])

# Configure templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# Request/Response Models
class ConvertToMarkdownRequest(BaseModel):
    """Request model for converting Confluence page to Markdown."""

    page_id: str = Field(..., description="Confluence page ID")
    save_to_storage: bool = Field(False, description="Whether to save to MinIO storage")


class ConvertToMarkdownResponse(BaseModel):
    """Response model for Markdown conversion."""

    markdown: str = Field(..., description="Converted Markdown content")
    saved_path: str | None = Field(None, description="Path in storage if saved")


class ConvertFromMarkdownRequest(BaseModel):
    """Request model for converting Markdown to Confluence page."""

    space_key: str = Field(..., description="Confluence space key")
    title: str = Field(..., description="Page title")
    markdown: str = Field(..., description="Markdown content to convert")
    parent_id: str | None = Field(None, description="Optional parent page ID")


class ConvertFromMarkdownResponse(BaseModel):
    """Response model for page creation."""

    page_id: str = Field(..., description="Created/updated page ID")
    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Page URL")


class SummarizePageRequest(BaseModel):
    """Request model for page summarization."""

    page_id: str = Field(..., description="Confluence page ID")
    model: str | None = Field(None, description="LLM model to use (default: mistral:latest)")


class SummarizePageResponse(BaseModel):
    """Response model for page summary."""

    summary: str = Field(..., description="Page summary")
    page_title: str = Field(..., description="Page title")


class BackupSpaceRequest(BaseModel):
    """Request model for space backup."""

    space_key: str = Field(..., description="Confluence space key")
    format: str = Field("html", description="Backup format (html)")


class BackupSpaceResponse(BaseModel):
    """Response model for space backup."""

    bucket: str = Field(..., description="MinIO bucket name")
    path: str = Field(..., description="Path in storage")
    page_count: int = Field(..., description="Number of pages backed up")


class StatisticsRequest(BaseModel):
    """Request model for space statistics."""

    space_key: str = Field(..., description="Confluence space key")


class StatisticsJobRequest(BaseModel):
    """Request model for async statistics job."""

    space_key: str = Field(..., description="Confluence space key")


class ModelsResponse(BaseModel):
    """Response model for available LLM models."""

    models: list[dict[str, Any]] = Field(..., description="List of available models")


@router.get("/confluence", response_class=HTMLResponse)
async def confluence_page(request: Request) -> HTMLResponse:
    """Render the Confluence integration page.

    Args:
        request: The incoming HTTP request

    Returns:
        HTMLResponse with the rendered Confluence page template
    """
    context = {
        "title": "Confluence Integration",
        "active_menu": "confluence",
    }
    return templates.TemplateResponse(request, "confluence.html", context)


@router.post("/confluence/convert-to-markdown", response_model=ConvertToMarkdownResponse)
async def convert_to_markdown(
    request: Request, payload: ConvertToMarkdownRequest
) -> ConvertToMarkdownResponse:
    """Convert a Confluence page to Markdown format via API.

    Args:
        request: The incoming HTTP request
        payload: Conversion request parameters

    Returns:
        Markdown content and optional storage path

    Raises:
        HTTPException: If conversion fails
    """
    api_base_url = request.app.state.config.api_base_url

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{api_base_url}/confluence/convert-to-markdown",
                json=payload.model_dump(),
            )

            if not response.is_success:
                error_detail = response.json().get("detail", response.text)
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            data = response.json()
            return ConvertToMarkdownResponse(**data)

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to API service: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@router.post("/confluence/convert-from-markdown", response_model=ConvertFromMarkdownResponse)
async def convert_from_markdown(
    request: Request, payload: ConvertFromMarkdownRequest
) -> ConvertFromMarkdownResponse:
    """Convert Markdown to Confluence page and create/update it via API.

    Args:
        request: The incoming HTTP request
        payload: Conversion request parameters

    Returns:
        Created/updated page information

    Raises:
        HTTPException: If conversion fails
    """
    api_base_url = request.app.state.config.api_base_url

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{api_base_url}/confluence/convert-from-markdown",
                json=payload.model_dump(),
            )

            if not response.is_success:
                error_detail = response.json().get("detail", response.text)
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            data = response.json()
            return ConvertFromMarkdownResponse(**data)

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to API service: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Page creation failed: {str(e)}")


@router.post("/confluence/summarize", response_model=SummarizePageResponse)
async def summarize_page(
    request: Request, payload: SummarizePageRequest
) -> SummarizePageResponse:
    """Summarize a Confluence page using LLM via API.

    Args:
        request: The incoming HTTP request
        payload: Summarization request parameters

    Returns:
        Page summary

    Raises:
        HTTPException: If summarization fails
    """
    api_base_url = request.app.state.config.api_base_url

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:  # Longer timeout for LLM
            response = await client.post(
                f"{api_base_url}/confluence/summarize",
                json=payload.model_dump(),
            )

            if not response.is_success:
                error_detail = response.json().get("detail", response.text)
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            data = response.json()
            return SummarizePageResponse(**data)

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to API service: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


@router.post("/confluence/backup-space", response_model=BackupSpaceResponse)
async def backup_space(
    request: Request, payload: BackupSpaceRequest
) -> BackupSpaceResponse:
    """Backup all pages from a Confluence space to MinIO storage via API.

    Args:
        request: The incoming HTTP request
        payload: Backup request parameters

    Returns:
        Backup information including storage location and page count

    Raises:
        HTTPException: If backup fails
    """
    api_base_url = request.app.state.config.api_base_url

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:  # Long timeout for backup
            response = await client.post(
                f"{api_base_url}/confluence/backup-space",
                json=payload.model_dump(),
            )

            if not response.is_success:
                error_detail = response.json().get("detail", response.text)
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            data = response.json()
            return BackupSpaceResponse(**data)

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to API service: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")


@router.post("/confluence/statistics")
async def get_statistics(request: Request, payload: StatisticsRequest) -> JSONResponse:
    """Get statistics for a Confluence space via API.

    Args:
        request: The incoming HTTP request
        payload: Statistics request parameters

    Returns:
        Space statistics including page count, size, contributors, etc.

    Raises:
        HTTPException: If statistics retrieval fails
    """
    api_base_url = request.app.state.config.api_base_url

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{api_base_url}/confluence/statistics",
                json=payload.model_dump(),
            )

            if not response.is_success:
                error_detail = response.json().get("detail", response.text)
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            return JSONResponse(content=response.json())

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to API service: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/confluence/models", response_model=ModelsResponse)
async def get_models(request: Request) -> ModelsResponse:
    """Get list of available LLM models for summarization via API.

    Args:
        request: The incoming HTTP request

    Returns:
        List of available models

    Raises:
        HTTPException: If model list retrieval fails
    """
    api_base_url = request.app.state.config.api_base_url

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{api_base_url}/confluence/models")

            if not response.is_success:
                error_detail = response.json().get("detail", response.text)
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            data = response.json()
            return ModelsResponse(**data)

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to API service: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.post("/confluence/statistics-async")
async def create_statistics_job(
    request: Request, payload: StatisticsJobRequest
) -> JSONResponse:
    """Create async statistics collection job via API.

    Args:
        request: The incoming HTTP request
        payload: Statistics job request parameters

    Returns:
        Job information including job_id and status

    Raises:
        HTTPException: If job creation fails
    """
    api_base_url = request.app.state.config.api_base_url

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_base_url}/confluence/statistics-async",
                json=payload.model_dump(),
            )

            if not response.is_success:
                error_detail = response.json().get("detail", response.text)
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            return JSONResponse(content=response.json())

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to API service: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create statistics job: {str(e)}"
        )


@router.get("/confluence/statistics-history/{space_key}")
async def get_statistics_history(
    request: Request,
    space_key: str,
    start_date: str | None = None,
    end_date: str | None = None,
    granularity: str = "raw",
    limit: int = 100,
) -> JSONResponse:
    """Get historical statistics for a Confluence space via API.

    Args:
        request: The incoming HTTP request
        space_key: Confluence space key
        start_date: Start date (ISO format, optional)
        end_date: End date (ISO format, optional)
        granularity: Data granularity (raw, hourly, daily)
        limit: Maximum number of entries

    Returns:
        Historical statistics data

    Raises:
        HTTPException: If query fails
    """
    api_base_url = request.app.state.config.api_base_url

    try:
        # Build query parameters
        params = {
            "granularity": granularity,
            "limit": limit,
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{api_base_url}/confluence/statistics-history/{space_key}",
                params=params,
            )

            if not response.is_success:
                error_detail = response.json().get("detail", response.text)
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            return JSONResponse(content=response.json())

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to API service: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve statistics history: {str(e)}"
        )
