"""LLM routes for API service.

This module provides endpoints for LLM operations via Ollama.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.api.exceptions import LLMError, ServiceUnavailableError
from src.api.models.schemas import GenerateRequest, GenerateResponse, ModelListResponse
from src.api.services.container import ServiceContainer
from src.api.services.ollama import OllamaService

router = APIRouter(prefix="/llm", tags=["llm"])


def get_container(request: Request) -> ServiceContainer:
    """Dependency to get service container from app state.

    Args:
        request: FastAPI request object

    Returns:
        Service container instance
    """
    return request.app.state.container


def get_ollama_service(container: ServiceContainer = Depends(get_container)) -> OllamaService:
    """Dependency to get Ollama service instance.

    Args:
        container: Service container

    Returns:
        Ollama service instance
    """
    return container.ollama


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    ollama: OllamaService = Depends(get_ollama_service),
) -> ModelListResponse:
    """List available LLM models.

    Args:
        ollama: Ollama service instance

    Returns:
        List of available models

    Raises:
        HTTPException: If listing fails
    """
    try:
        models = await ollama.list_models()
        return ModelListResponse(models=models)
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=e.message)
    except LLMError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/generate", response_model=GenerateResponse)
async def generate_text(
    request: GenerateRequest,
    ollama: OllamaService = Depends(get_ollama_service),
) -> GenerateResponse:
    """Generate text using an LLM model.

    Args:
        request: Generation request with model and prompt
        ollama: Ollama service instance

    Returns:
        Generated text response

    Raises:
        HTTPException: If generation fails
    """
    try:
        response_text = await ollama.generate_text(
            model=request.model,
            prompt=request.prompt,
            system=request.system,
        )
        return GenerateResponse(model=request.model, response=response_text)
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=e.message)
    except LLMError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/stream")
async def generate_text_stream(
    request: GenerateRequest,
    ollama: OllamaService = Depends(get_ollama_service),
) -> StreamingResponse:
    """Generate text with streaming response.

    Args:
        request: Generation request with model and prompt
        ollama: Ollama service instance

    Returns:
        Streaming response with generated text chunks

    Raises:
        HTTPException: If streaming fails
    """
    try:

        async def generate() -> bytes:
            async for chunk in ollama.generate_text_streaming(
                model=request.model,
                prompt=request.prompt,
                system=request.system,
            ):
                yield chunk.encode("utf-8")

        return StreamingResponse(generate(), media_type="text/plain")
    except (ServiceUnavailableError, LLMError) as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/pull/{model}")
async def pull_model(
    model: str,
    ollama: OllamaService = Depends(get_ollama_service),
) -> dict[str, str]:
    """Pull/download a model from Ollama registry.

    Args:
        model: Name of the model to pull
        ollama: Ollama service instance

    Returns:
        Success message

    Raises:
        HTTPException: If pull fails
    """
    try:
        await ollama.pull_model(model)
        return {"message": f"Model {model} pulled successfully"}
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=e.message)
    except LLMError as e:
        raise HTTPException(status_code=500, detail=e.message)
