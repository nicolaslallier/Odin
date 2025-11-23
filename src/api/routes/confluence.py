"""Confluence API routes for backend service.

This module provides API endpoints for all Confluence operations.
The API acts as the intermediary between the web portal and Confluence Cloud.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.exceptions import (
    ConfluenceError,
    DatabaseError,
    QueueError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    StorageError,
)
from src.api.models.schemas import (
    StatisticsCallbackRequest,
    StatisticsHistoryResponse,
    StatisticsJobRequest,
    StatisticsJobResponse,
)
from src.api.repositories.statistics_repository import StatisticsRepository
from src.api.services.confluence import ConfluenceService
from src.api.services.container import ServiceContainer
from src.api.services.ollama import OllamaService
from src.api.services.queue import QueueService
from src.api.services.storage import StorageService
from src.api.services.vault import VaultService
from src.api.services.websocket import WebSocketManager

router = APIRouter(prefix="/confluence", tags=["confluence"])


def get_container(request: Request) -> ServiceContainer:
    """Dependency to get service container from app state.

    Args:
        request: FastAPI request object

    Returns:
        Service container instance
    """
    return request.app.state.container


def get_storage_service(container: ServiceContainer = Depends(get_container)) -> StorageService:
    """Dependency to get storage service instance.

    Args:
        container: Service container

    Returns:
        Storage service instance
    """
    return container.storage


def get_vault_service(container: ServiceContainer = Depends(get_container)) -> VaultService:
    """Dependency to get Vault service instance.

    Args:
        container: Service container

    Returns:
        Vault service instance
    """
    return container.vault


def get_ollama_service(container: ServiceContainer = Depends(get_container)) -> OllamaService:
    """Dependency to get Ollama service instance.

    Args:
        container: Service container

    Returns:
        Ollama service instance
    """
    return container.ollama


def get_queue_service(container: ServiceContainer = Depends(get_container)) -> QueueService:
    """Dependency to get Queue service instance.

    Args:
        container: Service container

    Returns:
        Queue service instance
    """
    return container.queue


def get_websocket_manager(request: Request) -> WebSocketManager:
    """Dependency to get WebSocket manager instance.

    Args:
        request: FastAPI request object

    Returns:
        WebSocket manager instance
    """
    return request.app.state.websocket_manager


async def get_statistics_repository(
    container: ServiceContainer = Depends(get_container),
) -> StatisticsRepository:
    """Dependency to get Statistics repository instance.

    Args:
        container: Service container

    Returns:
        Statistics repository instance
    """
    session = container.database.get_async_session()
    return StatisticsRepository(session)


async def _get_confluence_service(vault: VaultService) -> ConfluenceService:
    """Get or create Confluence service with credentials from Vault.

    Args:
        vault: Vault service instance

    Returns:
        Initialized ConfluenceService instance

    Raises:
        HTTPException: If credentials not found or service unavailable
    """
    try:
        # Read Confluence credentials from Vault
        credentials = vault.read_secret("confluence/credentials")
        if not credentials:
            raise HTTPException(
                status_code=404,
                detail="Confluence credentials not found in Vault at path: confluence/credentials",
            )

        # Create and initialize Confluence service
        service = ConfluenceService(
            base_url=credentials["base_url"],
            email=credentials["email"],
            api_token=credentials["api_token"],
        )

        await service.initialize()
        return service

    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Confluence credentials not found in Vault",
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to initialize Confluence service: {str(e)}",
        )


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


class BackupFileRequest(BaseModel):
    """Request model for backing up a single Confluence page."""

    space_key: str = Field(..., description="Confluence space key")
    timestamp: str = Field(..., description="Backup timestamp")
    page_id: str = Field(..., description="Page ID")
    filename: str = Field(..., description="Filename for the backup")
    content: str = Field(..., description="Page content (HTML)")


class BackupFileResponse(BaseModel):
    """Response model for backup file upload."""

    success: bool = Field(..., description="Whether upload was successful")
    bucket: str = Field(..., description="Bucket name")
    object_key: str = Field(..., description="Object key in storage")
    size_bytes: int = Field(..., description="Size of uploaded file")


class ModelsResponse(BaseModel):
    """Response model for available LLM models."""

    models: list[dict[str, Any]] = Field(..., description="List of available models")


# Endpoints
@router.post("/convert-to-markdown", response_model=ConvertToMarkdownResponse)
async def convert_to_markdown(
    payload: ConvertToMarkdownRequest,
    vault: VaultService = Depends(get_vault_service),
    storage: StorageService = Depends(get_storage_service),
) -> ConvertToMarkdownResponse:
    """Convert a Confluence page to Markdown format.

    Args:
        payload: Conversion request parameters
        vault: Vault service instance
        storage: Storage service instance

    Returns:
        Markdown content and optional storage path

    Raises:
        HTTPException: If conversion fails
    """
    try:
        confluence_service = await _get_confluence_service(vault)

        # Convert page to Markdown
        markdown = await confluence_service.convert_page_to_markdown(payload.page_id)

        saved_path = None
        if payload.save_to_storage:
            # Save to MinIO storage
            bucket = "confluence-markdown"

            # Create bucket if it doesn't exist
            if not storage.bucket_exists(bucket):
                storage.create_bucket(bucket)

            # Generate filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            object_key = f"page_{payload.page_id}_{timestamp}.md"

            # Upload to storage
            markdown_bytes = markdown.encode("utf-8")
            storage.upload_file(
                bucket_name=bucket,
                object_name=object_key,
                data=BytesIO(markdown_bytes),
                length=len(markdown_bytes),
            )

            saved_path = f"{bucket}/{object_key}"

        await confluence_service.close()
        return ConvertToMarkdownResponse(markdown=markdown, saved_path=saved_path)

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@router.post("/convert-from-markdown", response_model=ConvertFromMarkdownResponse)
async def convert_from_markdown(
    payload: ConvertFromMarkdownRequest,
    vault: VaultService = Depends(get_vault_service),
) -> ConvertFromMarkdownResponse:
    """Convert Markdown to Confluence page and create/update it.

    Args:
        payload: Conversion request parameters
        vault: Vault service instance

    Returns:
        Created/updated page information

    Raises:
        HTTPException: If conversion fails
    """
    try:
        confluence_service = await _get_confluence_service(vault)

        # Convert Markdown to Confluence storage format
        html_content = confluence_service.convert_markdown_to_storage(payload.markdown)

        # Create or update page
        result = await confluence_service.create_or_update_page(
            space_key=payload.space_key,
            title=payload.title,
            content_html=html_content,
            parent_id=payload.parent_id,
        )

        # Construct page URL
        base_url = confluence_service.base_url
        web_ui_link = result.get("_links", {}).get("webui", "")
        page_url = f"{base_url}{web_ui_link}" if web_ui_link else ""

        await confluence_service.close()
        return ConvertFromMarkdownResponse(
            page_id=result["id"],
            title=result["title"],
            url=page_url,
        )

    except ConfluenceError as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Page creation failed: {str(e)}")


@router.post("/summarize", response_model=SummarizePageResponse)
async def summarize_page(
    payload: SummarizePageRequest,
    vault: VaultService = Depends(get_vault_service),
    ollama: OllamaService = Depends(get_ollama_service),
) -> SummarizePageResponse:
    """Summarize a Confluence page using LLM.

    Args:
        payload: Summarization request parameters
        vault: Vault service instance
        ollama: Ollama service instance

    Returns:
        Page summary

    Raises:
        HTTPException: If summarization fails
    """
    try:
        confluence_service = await _get_confluence_service(vault)

        # Get page content
        page_data = await confluence_service.get_page_by_id(payload.page_id)
        page_title = page_data.get("title", "")

        # Convert to Markdown for better LLM processing
        page_markdown = await confluence_service.convert_page_to_markdown(payload.page_id)

        # Use default model if not specified
        model = payload.model or "mistral:latest"

        # Check if model is available, pull if not
        available_models = await ollama.list_models()
        model_names = [m["name"] for m in available_models]
        if model not in model_names:
            # Try to pull the model
            await ollama.pull_model(model)

        # Generate summary
        system_prompt = (
            "You are a technical documentation expert. "
            "Summarize the following Confluence page concisely, "
            "highlighting key points, decisions, and action items."
        )
        summary = await ollama.generate_text(
            model=model,
            prompt=f"Page Title: {page_title}\n\nContent:\n{page_markdown}",
            system=system_prompt,
        )

        await confluence_service.close()
        return SummarizePageResponse(summary=summary, page_title=page_title)

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


@router.post("/backup-space", response_model=BackupSpaceResponse)
async def backup_space(
    payload: BackupSpaceRequest,
    vault: VaultService = Depends(get_vault_service),
    storage: StorageService = Depends(get_storage_service),
) -> BackupSpaceResponse:
    """Backup all pages from a Confluence space to MinIO storage.

    Args:
        payload: Backup request parameters
        vault: Vault service instance
        storage: Storage service instance

    Returns:
        Backup information including storage location and page count

    Raises:
        HTTPException: If backup fails
    """
    try:
        # Validate format
        if payload.format not in ["html"]:
            raise HTTPException(status_code=422, detail="Invalid format. Only 'html' is supported.")

        confluence_service = await _get_confluence_service(vault)

        # Backup all pages
        pages = await confluence_service.backup_space(payload.space_key)

        # Prepare storage
        bucket = "confluence-backups"
        if not storage.bucket_exists(bucket):
            storage.create_bucket(bucket)

        # Generate timestamp for backup folder
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base_path = f"{payload.space_key}/{timestamp}"

        # Upload each page to storage
        for page in pages:
            page_id = page["id"]
            page_title = page["title"]
            page_content = page.get("body", {}).get("storage", {}).get("value", "")

            # Create filename (sanitize title)
            safe_title = "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in page_title)
            filename = f"{page_id}_{safe_title}.html"
            object_key = f"{base_path}/{filename}"

            # Upload to storage
            content_bytes = page_content.encode("utf-8")
            storage.upload_file(
                bucket_name=bucket,
                object_name=object_key,
                data=BytesIO(content_bytes),
                length=len(content_bytes),
            )

        await confluence_service.close()
        return BackupSpaceResponse(
            bucket=bucket,
            path=base_path,
            page_count=len(pages),
        )

    except ConfluenceError as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")


@router.post("/statistics")
async def get_statistics(
    payload: StatisticsRequest,
    vault: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    """Get statistics for a Confluence space.

    Args:
        payload: Statistics request parameters
        vault: Vault service instance

    Returns:
        Space statistics including page count, size, contributors, etc.

    Raises:
        HTTPException: If statistics retrieval fails
    """
    confluence_service = None
    try:
        confluence_service = await _get_confluence_service(vault)

        # Get statistics
        stats = await confluence_service.get_space_statistics(payload.space_key)

        return stats

    except HTTPException:
        # Re-raise HTTPExceptions from _get_confluence_service without wrapping
        raise
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))
    except ConfluenceError as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
    finally:
        if confluence_service:
            await confluence_service.close()


@router.get("/models", response_model=ModelsResponse)
async def get_models(
    ollama: OllamaService = Depends(get_ollama_service),
) -> ModelsResponse:
    """Get list of available LLM models for summarization.

    Args:
        ollama: Ollama service instance

    Returns:
        List of available models

    Raises:
        HTTPException: If model list retrieval fails
    """
    try:
        # Get available models
        models = await ollama.list_models()

        return ModelsResponse(models=models)

    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.post("/backup-file", response_model=BackupFileResponse)
async def backup_confluence_file(
    request: BackupFileRequest,
    storage: StorageService = Depends(get_storage_service),
) -> BackupFileResponse:
    """Upload a single Confluence page backup to MinIO storage.

    This endpoint receives page content from the web portal and stores it
    in MinIO object storage.

    Args:
        request: Backup file request with page content
        storage: Storage service instance

    Returns:
        BackupFileResponse with upload details

    Raises:
        HTTPException: If storage operation fails
    """
    try:
        bucket = "confluence-backups"

        # Create bucket if it doesn't exist
        if not storage.bucket_exists(bucket):
            storage.create_bucket(bucket)

        # Generate object key
        object_key = f"{request.space_key}/{request.timestamp}/{request.filename}"

        # Convert content to bytes
        content_bytes = request.content.encode("utf-8")
        content_size = len(content_bytes)

        # Upload to storage
        storage.upload_file(
            bucket_name=bucket,
            object_name=object_key,
            data=BytesIO(content_bytes),
            length=content_size,
        )

        return BackupFileResponse(
            success=True,
            bucket=bucket,
            object_key=object_key,
            size_bytes=content_size,
        )

    except StorageError as e:
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e.message)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload backup: {str(e)}")


# In-memory job status cache (should be Redis in production)
_job_status_cache: dict[str, dict[str, Any]] = {}


@router.post("/statistics-async", response_model=StatisticsJobResponse)
async def create_statistics_job(
    payload: StatisticsJobRequest,
    queue: QueueService = Depends(get_queue_service),
) -> StatisticsJobResponse:
    """Create async statistics collection job.

    This endpoint initiates asynchronous statistics collection for a
    Confluence space. The job is queued and processed by the worker,
    with results delivered via WebSocket when complete.

    Args:
        payload: Statistics job request
        queue: Queue service instance

    Returns:
        Job information including job_id and status

    Raises:
        HTTPException: If job creation fails
    """
    try:
        # Generate unique job ID
        job_id = str(uuid4())

        # Create event payload for RabbitMQ
        event = {
            "job_id": job_id,
            "space_key": payload.space_key,
            "timestamp": datetime.utcnow().isoformat(),
            "callback_url": f"{os.environ.get('API_CALLBACK_URL', 'http://odin-api:8001')}/internal/statistics-callback",
        }

        # Declare queue if it doesn't exist
        queue_name = "confluence.statistics.requests"
        queue.declare_queue(queue_name, durable=True)

        # Publish event to RabbitMQ
        queue.publish_message(queue_name, json.dumps(event), persistent=True)

        # Store job status in cache
        job_status = {
            "job_id": job_id,
            "space_key": payload.space_key,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "estimated_time_seconds": 30,  # Rough estimate
        }
        _job_status_cache[job_id] = job_status

        return StatisticsJobResponse(**job_status)

    except QueueError as e:
        raise HTTPException(status_code=503, detail=f"Queue service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create statistics job: {str(e)}")


@router.post("/internal/statistics-callback")
async def receive_statistics_callback(
    payload: StatisticsCallbackRequest,
    repository: StatisticsRepository = Depends(get_statistics_repository),
    websocket_manager: WebSocketManager = Depends(get_websocket_manager),
) -> dict[str, str]:
    """Internal endpoint to receive statistics from worker.

    This endpoint is called by the worker after collecting statistics.
    It stores the statistics in TimescaleDB and broadcasts via WebSocket.

    Args:
        payload: Statistics callback data from worker
        repository: Statistics repository instance
        websocket_manager: WebSocket manager instance

    Returns:
        Success confirmation

    Raises:
        HTTPException: If callback processing fails
    """
    try:
        # Validate job_id exists
        if payload.job_id not in _job_status_cache:
            raise HTTPException(status_code=404, detail=f"Job not found: {payload.job_id}")

        # Update job status
        _job_status_cache[payload.job_id]["status"] = payload.status
        _job_status_cache[payload.job_id]["completed_at"] = datetime.utcnow().isoformat()

        if payload.status == "completed":
            # Save statistics to TimescaleDB
            stats_dict = payload.statistics.model_dump()

            # Parse timestamp
            timestamp = datetime.fromisoformat(
                stats_dict["timestamp"].replace("Z", "+00:00")
            )

            stats_id = await repository.save_statistics(
                space_key=payload.space_key,
                space_name=stats_dict.get("space_name"),
                timestamp=timestamp,
                statistics={
                    "basic": stats_dict.get("basic", {}),
                    "detailed": stats_dict.get("detailed", {}),
                    "comprehensive": stats_dict.get("comprehensive", {}),
                    "collection_time_seconds": stats_dict.get("collection_time_seconds"),
                },
            )

            # Store statistics in job cache
            _job_status_cache[payload.job_id]["statistics"] = stats_dict
            _job_status_cache[payload.job_id]["stats_id"] = stats_id

            # Broadcast to WebSocket clients
            await websocket_manager.broadcast_statistics(
                space_key=payload.space_key,
                job_id=payload.job_id,
                statistics=stats_dict,
                status="completed",
            )

        elif payload.status == "failed":
            # Store error message
            _job_status_cache[payload.job_id]["error_message"] = payload.error_message

            # Broadcast failure to WebSocket clients
            await websocket_manager.broadcast_statistics(
                space_key=payload.space_key,
                job_id=payload.job_id,
                statistics={},
                status="failed",
            )

        return {"status": "success", "message": "Statistics received"}

    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process statistics callback: {str(e)}"
        )


@router.get("/statistics-history/{space_key}", response_model=StatisticsHistoryResponse)
async def get_statistics_history(
    space_key: str,
    start_date: str | None = None,
    end_date: str | None = None,
    granularity: str = "raw",
    limit: int = 100,
    repository: StatisticsRepository = Depends(get_statistics_repository),
) -> StatisticsHistoryResponse:
    """Get historical statistics for a Confluence space.

    This endpoint retrieves time series data for a space from TimescaleDB,
    with support for different granularities (raw, hourly, daily).

    Args:
        space_key: Confluence space key
        start_date: Start date (ISO format, default: 7 days ago)
        end_date: End date (ISO format, default: now)
        granularity: Data granularity (raw, hourly, daily)
        limit: Maximum number of entries (1-1000)
        repository: Statistics repository instance

    Returns:
        Historical statistics data

    Raises:
        HTTPException: If query fails
    """
    try:
        # Parse dates
        end_dt = (
            datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            if end_date
            else datetime.utcnow()
        )
        start_dt = (
            datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            if start_date
            else end_dt - timedelta(days=7)
        )

        # Validate granularity
        if granularity not in ["raw", "hourly", "daily"]:
            raise HTTPException(
                status_code=422, detail="Invalid granularity. Must be 'raw', 'hourly', or 'daily'"
            )

        # Validate limit
        if limit < 1 or limit > 1000:
            raise HTTPException(status_code=422, detail="Limit must be between 1 and 1000")

        # Query historical statistics
        entries = await repository.get_statistics_history(
            space_key=space_key,
            start_date=start_dt,
            end_date=end_dt,
            granularity=granularity,
            limit=limit,
        )

        return StatisticsHistoryResponse(
            space_key=space_key,
            entries=[
                {
                    "id": entry.get("id", 0),
                    "space_key": entry.get("space_key", space_key),
                    "space_name": entry.get("space_name"),
                    "timestamp": entry.get("timestamp", ""),
                    "total_pages": entry.get("total_pages", 0),
                    "total_size_bytes": entry.get("total_size_bytes", 0),
                    "contributor_count": entry.get("contributor_count", 0),
                    "collection_time_seconds": entry.get("collection_time_seconds"),
                    "metadata": entry.get("metadata", {}),
                }
                for entry in entries
            ],
            total=len(entries),
            time_range={
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
            },
            granularity=granularity,
        )

    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve statistics history: {str(e)}"
        )

