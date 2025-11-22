"""LLM routes for API service.

This module provides endpoints for LLM operations via Ollama.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.api.config import APIConfig, get_config
from src.api.models.schemas import GenerateRequest, GenerateResponse, ModelListResponse
from src.api.services.ollama import OllamaService

router = APIRouter(prefix="/llm", tags=["llm"])


def get_ollama_service(config: APIConfig = Depends(get_config)) -> OllamaService:
    """Dependency to get Ollama service instance.

    Args:
        config: API configuration

    Returns:
        Ollama service instance
    """
    return OllamaService(base_url=config.ollama_base_url)


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    ollama: OllamaService = Depends(get_ollama_service),
) -> ModelListResponse:
    """List available LLM models.

    Args:
        ollama: Ollama service instance

    Returns:
        List of available models
    """
    try:
        models = await ollama.list_models()
        return ModelListResponse(models=models)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    """
    try:
        response_text = await ollama.generate_text(
            model=request.model,
            prompt=request.prompt,
            system=request.system,
        )
        return GenerateResponse(model=request.model, response=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

