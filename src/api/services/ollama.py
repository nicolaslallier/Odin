"""Ollama LLM service client.

This module provides LLM operations using Ollama for text generation
and model management in the API service.
"""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Optional

import httpx


class OllamaService:
    """Ollama LLM service client.

    This class provides LLM operations including text generation and model management.

    Attributes:
        base_url: Ollama API base URL
    """

    def __init__(self, base_url: str) -> None:
        """Initialize Ollama service with base URL.

        Args:
            base_url: Ollama API base URL (e.g., http://ollama:11434)
        """
        self.base_url = base_url

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models.

        Returns:
            List of model information dictionaries
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/tags")
            data = response.json()
            return data.get("models", [])

    async def generate_text(
        self, model: str, prompt: str, system: Optional[str] = None
    ) -> str:
        """Generate text using a model.

        Args:
            model: Name of the model to use
            prompt: Text prompt for generation
            system: Optional system prompt for context

        Returns:
            Generated text
        """
        async with httpx.AsyncClient() as client:
            payload: dict[str, Any] = {
                "model": model,
                "prompt": prompt,
                "stream": False,
            }
            
            if system:
                payload["system"] = system
            
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60.0,
            )
            data = response.json()
            return data["response"]

    async def generate_text_streaming(
        self, model: str, prompt: str, system: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generate text with streaming response.

        Args:
            model: Name of the model to use
            prompt: Text prompt for generation
            system: Optional system prompt for context

        Yields:
            Text chunks as they are generated
        """
        async with httpx.AsyncClient() as client:
            payload: dict[str, Any] = {
                "model": model,
                "prompt": prompt,
                "stream": True,
            }
            
            if system:
                payload["system"] = system
            
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60.0,
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]

    async def pull_model(self, model: str) -> bool:
        """Pull/download a model.

        Args:
            model: Name of the model to pull

        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model},
                    timeout=300.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def delete_model(self, model: str) -> bool:
        """Delete a model.

        Args:
            model: Name of the model to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/api/delete",
                    json={"name": model},
                )
                return response.status_code == 200
        except Exception:
            return False

    async def health_check(self) -> bool:
        """Check if Ollama connection is healthy.

        Returns:
            True if Ollama is accessible, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False

