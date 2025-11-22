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

