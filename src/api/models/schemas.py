"""Pydantic models and schemas for API requests and responses.

This module defines all request and response models used by the API endpoints.
"""

from __future__ import annotations

from typing import Any, Optional

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
    message: Optional[str] = Field(None, description="Message content")


# Secret Management Models
class SecretRequest(BaseModel):
    """Secret write request model."""

    path: str = Field(..., description="Secret path")
    data: dict[str, Any] = Field(..., description="Secret data")


class SecretResponse(BaseModel):
    """Secret read response model."""

    path: str = Field(..., description="Secret path")
    data: Optional[dict[str, Any]] = Field(None, description="Secret data")


# LLM Models
class GenerateRequest(BaseModel):
    """Text generation request model."""

    model: str = Field(..., description="Model name")
    prompt: str = Field(..., description="Text prompt")
    system: Optional[str] = Field(None, description="Optional system prompt")


class GenerateResponse(BaseModel):
    """Text generation response model."""

    model: str = Field(..., description="Model used")
    response: str = Field(..., description="Generated text")


class ModelInfo(BaseModel):
    """Model information model with extended details."""

    name: str = Field(..., description="Model name")
    size: Optional[int] = Field(None, description="Model size in bytes")
    digest: Optional[str] = Field(None, description="Model digest/hash")
    modified_at: Optional[str] = Field(None, description="Last modification time")


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

    id: Optional[int] = Field(None, description="Item ID")
    name: str = Field(..., description="Item name")
    description: Optional[str] = Field(None, description="Item description")
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
    logger: Optional[str] = Field(None, description="Logger name")
    message: str = Field(..., description="Log message")
    module: Optional[str] = Field(None, description="Module name")
    function: Optional[str] = Field(None, description="Function name")
    line: Optional[int] = Field(None, description="Line number")
    exception: Optional[str] = Field(None, description="Exception traceback")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    task_id: Optional[str] = Field(None, description="Task correlation ID")
    user_id: Optional[str] = Field(None, description="User ID")
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

    start_time: Optional[str] = Field(None, description="Start time (ISO format)")
    end_time: Optional[str] = Field(None, description="End time (ISO format)")
    level: Optional[str] = Field(None, description="Log level filter")
    service: Optional[str] = Field(None, description="Service name filter")
    search: Optional[str] = Field(None, description="Search term for message content")
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

    log_ids: Optional[list[int]] = Field(None, description="Specific log IDs to analyze")
    search_criteria: Optional[LogSearchRequest] = Field(
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
    recommendations: list[str] = Field(
        default_factory=list, description="Recommendations"
    )
    patterns: list[dict[str, Any]] = Field(
        default_factory=list, description="Identified patterns"
    )
    related_logs: list[int] = Field(
        default_factory=list, description="IDs of related log entries"
    )

