"""Pydantic models and schemas for API requests and responses.

This module defines all request and response models used by the API endpoints.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# Health Check Models
class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Overall health status")
    service: str = Field(..., description="Service name")


class ServiceHealthResponse(BaseModel):
    """Individual service health response model."""

    database: bool = Field(..., description="Database connection status")
    storage: bool = Field(..., description="Storage connection status")
    queue: bool = Field(..., description="Queue connection status")
    vault: bool = Field(..., description="Vault connection status")
    ollama: bool = Field(..., description="Ollama connection status")


# File Upload/Download Models
class FileUploadResponse(BaseModel):
    """File upload response model."""

    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="Object key/name")
    message: str = Field(..., description="Success message")


class FileListResponse(BaseModel):
    """File list response model."""

    bucket: str = Field(..., description="Bucket name")
    files: list[str] = Field(..., description="List of file names")


# Message Queue Models
class MessageRequest(BaseModel):
    """Message send request model."""

    queue: str = Field(..., description="Queue name")
    message: str = Field(..., description="Message content")


class MessageResponse(BaseModel):
    """Message response model."""

    queue: str = Field(..., description="Queue name")
    message: str | None = Field(None, description="Message content")


# Secret Management Models
class SecretRequest(BaseModel):
    """Secret write request model."""

    path: str = Field(..., description="Secret path")
    data: dict[str, Any] = Field(..., description="Secret data")


class SecretResponse(BaseModel):
    """Secret read response model."""

    path: str = Field(..., description="Secret path")
    data: dict[str, Any] | None = Field(None, description="Secret data")


# LLM Models
class GenerateRequest(BaseModel):
    """Text generation request model."""

    model: str = Field(..., description="Model name")
    prompt: str = Field(..., description="Text prompt")
    system: str | None = Field(None, description="Optional system prompt")


class GenerateResponse(BaseModel):
    """Text generation response model."""

    model: str = Field(..., description="Model used")
    response: str = Field(..., description="Generated text")


class ModelInfo(BaseModel):
    """Model information model with extended details."""

    name: str = Field(..., description="Model name")
    size: int | None = Field(None, description="Model size in bytes")
    digest: str | None = Field(None, description="Model digest/hash")
    modified_at: str | None = Field(None, description="Last modification time")


class ModelListResponse(BaseModel):
    """Model list response model."""

    models: list[ModelInfo] = Field(..., description="List of available models")


# Circuit Breaker Models
class CircuitBreakerState(BaseModel):
    """Circuit breaker state information."""

    name: str = Field(..., description="Circuit breaker name")
    state: str = Field(..., description="Current state (closed, open, half_open)")
    failure_count: int = Field(..., description="Number of consecutive failures")


class CircuitBreakerStates(BaseModel):
    """Circuit breaker states for all services."""

    breakers: dict[str, str] = Field(..., description="Map of service name to state")


# Data CRUD Models (generic example)
class DataItem(BaseModel):
    """Generic data item model."""

    id: int | None = Field(None, description="Item ID")
    name: str = Field(..., description="Item name")
    description: str | None = Field(None, description="Item description")
    data: dict[str, Any] = Field(default_factory=dict, description="Additional data")


class DataListResponse(BaseModel):
    """Data list response model."""

    items: list[DataItem] = Field(..., description="List of data items")
    total: int = Field(..., description="Total number of items")


# Log Management Models
class LogEntry(BaseModel):
    """Single log entry model."""

    id: int = Field(..., description="Log entry ID")
    timestamp: str = Field(..., description="Log timestamp (ISO format)")
    level: str = Field(..., description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    service: str = Field(..., description="Service name (api, worker, web, nginx)")
    logger: str | None = Field(None, description="Logger name")
    message: str = Field(..., description="Log message")
    module: str | None = Field(None, description="Module name")
    function: str | None = Field(None, description="Function name")
    line: int | None = Field(None, description="Line number")
    exception: str | None = Field(None, description="Exception traceback")
    request_id: str | None = Field(None, description="Request correlation ID")
    task_id: str | None = Field(None, description="Task correlation ID")
    user_id: str | None = Field(None, description="User ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: str = Field(..., description="Database insertion timestamp (ISO format)")


class LogListResponse(BaseModel):
    """Paginated log list response model."""

    logs: list[LogEntry] = Field(..., description="List of log entries")
    total: int = Field(..., description="Total number of matching logs")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Offset for pagination")


class LogSearchRequest(BaseModel):
    """Log search request model."""

    start_time: str | None = Field(None, description="Start time (ISO format)")
    end_time: str | None = Field(None, description="End time (ISO format)")
    level: str | None = Field(None, description="Log level filter")
    service: str | None = Field(None, description="Service name filter")
    search: str | None = Field(None, description="Search term for message content")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")


class LogStatisticsByLevel(BaseModel):
    """Log statistics by level."""

    DEBUG: int = Field(default=0, description="Number of DEBUG logs")
    INFO: int = Field(default=0, description="Number of INFO logs")
    WARNING: int = Field(default=0, description="Number of WARNING logs")
    ERROR: int = Field(default=0, description="Number of ERROR logs")
    CRITICAL: int = Field(default=0, description="Number of CRITICAL logs")


class LogStatistics(BaseModel):
    """Aggregated log statistics."""

    time_range: dict[str, str] = Field(..., description="Time range for statistics")
    total_logs: int = Field(..., description="Total number of logs")
    by_level: LogStatisticsByLevel = Field(..., description="Statistics by log level")
    by_service: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Statistics by service and level"
    )


class LogAnalysisRequest(BaseModel):
    """LLM log analysis request model."""

    log_ids: list[int] | None = Field(None, description="Specific log IDs to analyze")
    search_criteria: LogSearchRequest | None = Field(
        None, description="Search criteria to select logs"
    )
    analysis_type: str = Field(
        default="root_cause",
        description="Type of analysis (root_cause, pattern, anomaly, correlation)",
    )
    max_logs: int = Field(
        default=50, ge=1, le=200, description="Maximum logs to include in analysis"
    )


class LogAnalysisResponse(BaseModel):
    """LLM log analysis response model."""

    analysis_type: str = Field(..., description="Type of analysis performed")
    logs_analyzed: int = Field(..., description="Number of logs analyzed")
    summary: str = Field(..., description="Analysis summary")
    findings: list[str] = Field(default_factory=list, description="Key findings")
    recommendations: list[str] = Field(default_factory=list, description="Recommendations")
    patterns: list[dict[str, Any]] = Field(default_factory=list, description="Identified patterns")
    related_logs: list[int] = Field(default_factory=list, description="IDs of related log entries")


# Image Analysis Models
class ImageMetadata(BaseModel):
    """Image file metadata model."""

    bucket: str = Field(..., description="MinIO bucket name")
    object_key: str = Field(..., description="Unique object key in storage")
    content_type: str = Field(..., description="MIME content type")
    size_bytes: int = Field(..., description="File size in bytes")


class ImageAnalysisResponse(BaseModel):
    """Image analysis response model."""

    id: int = Field(..., description="Image analysis ID")
    filename: str = Field(..., description="Original filename")
    llm_description: str | None = Field(None, description="LLM-generated description")
    model_used: str | None = Field(None, description="Model used for analysis")
    metadata: ImageMetadata = Field(..., description="Image storage metadata")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: str = Field(..., description="Last update timestamp (ISO format)")


class ImageAnalysisListResponse(BaseModel):
    """Image analysis list response model."""

    analyses: list[ImageAnalysisResponse] = Field(..., description="List of image analyses")
    total: int = Field(..., description="Total number of analyses")


# Async Confluence Statistics Models
class StatisticsJobRequest(BaseModel):
    """Request model for initiating async statistics collection."""

    space_key: str = Field(..., description="Confluence space key", min_length=1, max_length=255)


class StatisticsJobResponse(BaseModel):
    """Response model for async statistics job creation."""

    job_id: str = Field(..., description="Unique job identifier (UUID)")
    space_key: str = Field(..., description="Confluence space key")
    status: str = Field(..., description="Job status (pending, processing, completed, failed)")
    estimated_time_seconds: int | None = Field(
        None, description="Estimated time to completion in seconds"
    )
    created_at: str = Field(..., description="Job creation timestamp (ISO format)")


class BasicStatistics(BaseModel):
    """Basic Confluence space statistics."""

    total_pages: int = Field(..., description="Total number of pages")
    total_size_bytes: int = Field(..., description="Total size in bytes")
    contributor_count: int = Field(..., description="Number of unique contributors")
    last_updated: str | None = Field(None, description="Last update timestamp (ISO format)")


class DetailedStatistics(BaseModel):
    """Detailed Confluence space statistics."""

    page_breakdown_by_type: dict[str, int] = Field(
        default_factory=dict, description="Page count by type (page, blogpost, etc.)"
    )
    attachment_stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Attachment statistics (count, total_size, types)",
    )
    version_count: int = Field(default=0, description="Total number of page versions")


class ComprehensiveStatistics(BaseModel):
    """Comprehensive Confluence space statistics."""

    user_activity: dict[str, Any] = Field(
        default_factory=dict, description="User activity breakdown (pages per user)"
    )
    page_views: dict[str, Any] = Field(
        default_factory=dict, description="Page view analytics (if available)"
    )
    comment_counts: dict[str, Any] = Field(
        default_factory=dict, description="Comment count aggregation"
    )
    link_analysis: dict[str, Any] = Field(
        default_factory=dict, description="Internal/external link analysis"
    )


class ConfluenceStatistics(BaseModel):
    """Complete Confluence space statistics."""

    space_key: str = Field(..., description="Confluence space key")
    space_name: str | None = Field(None, description="Confluence space name")
    timestamp: str = Field(..., description="Collection timestamp (ISO format)")
    basic: BasicStatistics = Field(..., description="Basic statistics")
    detailed: DetailedStatistics = Field(..., description="Detailed statistics")
    comprehensive: ComprehensiveStatistics = Field(..., description="Comprehensive statistics")
    collection_time_seconds: float | None = Field(
        None, description="Time taken to collect statistics"
    )


class StatisticsCallbackRequest(BaseModel):
    """Request model for worker callback with collected statistics."""

    job_id: str = Field(..., description="Job identifier matching the original request")
    space_key: str = Field(..., description="Confluence space key")
    statistics: ConfluenceStatistics = Field(..., description="Collected statistics")
    status: str = Field(..., description="Collection status (completed, failed)")
    error_message: str | None = Field(None, description="Error message if status is failed")


class StatisticsHistoryEntry(BaseModel):
    """Single historical statistics entry."""

    id: int = Field(..., description="Entry ID")
    space_key: str = Field(..., description="Confluence space key")
    space_name: str | None = Field(None, description="Confluence space name")
    timestamp: str = Field(..., description="Collection timestamp (ISO format)")
    total_pages: int = Field(..., description="Total number of pages")
    total_size_bytes: int = Field(..., description="Total size in bytes")
    contributor_count: int = Field(..., description="Number of unique contributors")
    collection_time_seconds: float | None = Field(
        None, description="Time taken to collect statistics"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (detailed/comprehensive stats)"
    )


class StatisticsHistoryResponse(BaseModel):
    """Response model for historical statistics query."""

    space_key: str = Field(..., description="Confluence space key")
    entries: list[StatisticsHistoryEntry] = Field(..., description="Historical statistics entries")
    total: int = Field(..., description="Total number of entries")
    time_range: dict[str, str] = Field(..., description="Time range of data (start, end)")
    granularity: str = Field(..., description="Data granularity (raw, hourly, daily)")


class StatisticsJobStatusResponse(BaseModel):
    """Response model for job status query."""

    job_id: str = Field(..., description="Job identifier")
    space_key: str = Field(..., description="Confluence space key")
    status: str = Field(..., description="Job status (pending, processing, completed, failed)")
    progress: int | None = Field(None, description="Progress percentage (0-100)")
    created_at: str = Field(..., description="Job creation timestamp (ISO format)")
    completed_at: str | None = Field(None, description="Job completion timestamp (ISO format)")
    statistics: ConfluenceStatistics | None = Field(None, description="Statistics (if completed)")
    error_message: str | None = Field(None, description="Error message (if failed)")
