"""Image analysis routes for API service.

This module provides endpoints for image upload, analysis, and management.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from src.api.exceptions import LLMError, ResourceNotFoundError, StorageError, ValidationError
from src.api.models.schemas import (
    ImageAnalysisListResponse,
    ImageAnalysisResponse,
    ImageMetadata,
)
from src.api.services.container import ServiceContainer
from src.api.services.image_analysis import ImageAnalysisService

router = APIRouter(prefix="/llm/analyze-image", tags=["image-analysis"])


def get_container(request: Request) -> ServiceContainer:
    """Dependency to get service container from app state.

    Args:
        request: FastAPI request object

    Returns:
        Service container instance
    """
    return request.app.state.container


def get_image_analysis_service(
    container: ServiceContainer = Depends(get_container),
) -> ImageAnalysisService:
    """Dependency to get image analysis service instance.

    Args:
        container: Service container

    Returns:
        Image analysis service instance
    """
    return container.image_analysis


@router.post("", response_model=ImageAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    service: ImageAnalysisService = Depends(get_image_analysis_service),
) -> ImageAnalysisResponse:
    """Upload and analyze an image using a vision-capable LLM model.

    Args:
        file: Image file to analyze (JPEG, PNG, WebP, GIF)
        prompt: Optional prompt for analysis (default: "Describe this image")
        model: Optional model name (default: configured default model)
        service: Image analysis service instance

    Returns:
        Analysis response with image metadata and LLM description

    Raises:
        HTTPException: If analysis fails (400 for validation, 500 for other errors)
    """
    try:
        # Read file content
        file_content = await file.read()
        
        # Get content type (with fallback)
        content_type = file.content_type or "application/octet-stream"
        
        # Analyze and store
        analysis = await service.analyze_and_store(
            filename=file.filename or "unknown",
            file_data=file_content,
            content_type=content_type,
            prompt=prompt,
            model=model,
        )
        
        # Convert to response model
        return ImageAnalysisResponse(
            id=analysis.id,
            filename=analysis.filename,
            llm_description=analysis.llm_description,
            model_used=analysis.model_used,
            metadata=ImageMetadata(
                bucket=analysis.bucket,
                object_key=analysis.object_key,
                content_type=analysis.content_type,
                size_bytes=analysis.size_bytes,
            ),
            created_at=analysis.created_at.isoformat(),
            updated_at=analysis.updated_at.isoformat(),
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except (StorageError, LLMError) as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{image_id}", response_model=ImageAnalysisResponse)
async def get_analysis(
    image_id: int,
    service: ImageAnalysisService = Depends(get_image_analysis_service),
) -> ImageAnalysisResponse:
    """Get image analysis by ID.

    Args:
        image_id: ID of the image analysis
        service: Image analysis service instance

    Returns:
        Analysis response with metadata and description

    Raises:
        HTTPException: If analysis not found (404) or retrieval fails (500)
    """
    try:
        analysis = await service.get_analysis(image_id)
        
        return ImageAnalysisResponse(
            id=analysis.id,
            filename=analysis.filename,
            llm_description=analysis.llm_description,
            model_used=analysis.model_used,
            metadata=ImageMetadata(
                bucket=analysis.bucket,
                object_key=analysis.object_key,
                content_type=analysis.content_type,
                size_bytes=analysis.size_bytes,
            ),
            created_at=analysis.created_at.isoformat(),
            updated_at=analysis.updated_at.isoformat(),
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=ImageAnalysisListResponse)
async def list_analyses(
    service: ImageAnalysisService = Depends(get_image_analysis_service),
) -> ImageAnalysisListResponse:
    """List all image analyses.

    Args:
        service: Image analysis service instance

    Returns:
        List of all image analyses with pagination info

    Raises:
        HTTPException: If retrieval fails (500)
    """
    try:
        analyses = await service.list_analyses()
        
        # Convert to response models
        response_analyses = [
            ImageAnalysisResponse(
                id=analysis.id,
                filename=analysis.filename,
                llm_description=analysis.llm_description,
                model_used=analysis.model_used,
                metadata=ImageMetadata(
                    bucket=analysis.bucket,
                    object_key=analysis.object_key,
                    content_type=analysis.content_type,
                    size_bytes=analysis.size_bytes,
                ),
                created_at=analysis.created_at.isoformat(),
                updated_at=analysis.updated_at.isoformat(),
            )
            for analysis in analyses
        ]
        
        return ImageAnalysisListResponse(
            analyses=response_analyses,
            total=len(response_analyses),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{image_id}")
async def delete_analysis(
    image_id: int,
    service: ImageAnalysisService = Depends(get_image_analysis_service),
) -> dict[str, str]:
    """Delete image analysis and associated image file.

    Args:
        image_id: ID of the image analysis to delete
        service: Image analysis service instance

    Returns:
        Confirmation message

    Raises:
        HTTPException: If analysis not found (404) or deletion fails (500)
    """
    try:
        await service.delete_analysis(image_id)
        return {"message": f"Image analysis {image_id} deleted successfully"}
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

