"""Ollama LLM service client.

This module provides LLM operations using Ollama for text generation
and model management in the API service.
"""

from __future__ import annotations

import base64
import json
from typing import Any, AsyncGenerator, Optional

import httpx

from src.api.exceptions import LLMError, ServiceUnavailableError


class OllamaService:
    """Ollama LLM service client.

    This class provides LLM operations including text generation and model management.
    It maintains a persistent HTTP client for connection pooling and reuse.

    Attributes:
        base_url: Ollama API base URL
    """

    def __init__(self, base_url: str) -> None:
        """Initialize Ollama service with base URL.

        Args:
            base_url: Ollama API base URL (e.g., http://ollama:11434)
        """
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize the HTTP client for connection pooling.

        This method creates a persistent HTTP client that will be reused
        for all requests, improving performance and resource usage.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get the HTTP client instance.

        Returns:
            HTTP client instance

        Raises:
            ServiceUnavailableError: If client not initialized
        """
        if self._client is None:
            raise ServiceUnavailableError(
                "Ollama service not initialized. Call initialize() first."
            )
        return self._client

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models.

        Returns:
            List of model information dictionaries with fields:
            - name: Model name
            - size: Model size in bytes (optional)
            - digest: Model digest/hash (optional)  
            - modified_at: Last modification time (optional)

        Raises:
            LLMError: If failed to list models
            ServiceUnavailableError: If Ollama service is unreachable
        """
        try:
            client = self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            
            # Extract and normalize model information
            models = data.get("models", [])
            normalized_models = []
            for model in models:
                normalized_model = {
                    "name": model.get("name", "unknown"),
                    "size": model.get("size"),
                    "digest": model.get("digest"),
                    "modified_at": model.get("modified_at"),
                }
                normalized_models.append(normalized_model)
            
            return normalized_models
        except httpx.HTTPStatusError as e:
            raise LLMError(f"Failed to list models: {e}", {"status_code": e.response.status_code})
        except httpx.RequestError as e:
            raise ServiceUnavailableError(f"Ollama service unreachable: {e}")

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

        Raises:
            LLMError: If text generation fails
            ServiceUnavailableError: If Ollama service is unreachable
        """
        try:
            client = self._get_client()
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
            )
            response.raise_for_status()
            data = response.json()
            return data["response"]
        except httpx.HTTPStatusError as e:
            raise LLMError(
                f"Failed to generate text: {e}",
                {"status_code": e.response.status_code, "model": model},
            )
        except httpx.RequestError as e:
            raise ServiceUnavailableError(f"Ollama service unreachable: {e}")

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

        Raises:
            LLMError: If text generation fails
            ServiceUnavailableError: If Ollama service is unreachable
        """
        try:
            client = self._get_client()
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
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
        except httpx.HTTPStatusError as e:
            raise LLMError(
                f"Failed to generate streaming text: {e}",
                {"status_code": e.response.status_code, "model": model},
            )
        except httpx.RequestError as e:
            raise ServiceUnavailableError(f"Ollama service unreachable: {e}")

    async def pull_model(self, model: str) -> bool:
        """Pull/download a model.

        Args:
            model: Name of the model to pull

        Returns:
            True if successful, False otherwise

        Raises:
            LLMError: If model pull fails
            ServiceUnavailableError: If Ollama service is unreachable
        """
        try:
            client = self._get_client()
            response = await client.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                timeout=httpx.Timeout(300.0),
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            raise LLMError(
                f"Failed to pull model: {e}",
                {"status_code": e.response.status_code, "model": model},
            )
        except httpx.RequestError as e:
            raise ServiceUnavailableError(f"Ollama service unreachable: {e}")

    async def delete_model(self, model: str) -> bool:
        """Delete a model.

        Args:
            model: Name of the model to delete

        Returns:
            True if successful, False otherwise

        Raises:
            LLMError: If model deletion fails
            ServiceUnavailableError: If Ollama service is unreachable
        """
        try:
            client = self._get_client()
            response = await client.delete(
                f"{self.base_url}/api/delete",
                json={"name": model},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            raise LLMError(
                f"Failed to delete model: {e}",
                {"status_code": e.response.status_code, "model": model},
            )
        except httpx.RequestError as e:
            raise ServiceUnavailableError(f"Ollama service unreachable: {e}")

    async def analyze_image(
        self, model: str, prompt: str, image_data: bytes, system: Optional[str] = None
    ) -> str:
        """Analyze an image using a vision-capable model.

        Args:
            model: Name of the vision model to use (e.g., 'llava:latest')
            prompt: Text prompt for image analysis
            image_data: Image data as bytes
            system: Optional system prompt for context

        Returns:
            Generated image analysis text

        Raises:
            LLMError: If image analysis fails
            ServiceUnavailableError: If Ollama service is unreachable
        """
        try:
            client = self._get_client()
            
            # Encode image as base64
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            
            payload: dict[str, Any] = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "images": [image_base64],
            }
            
            if system:
                payload["system"] = system
            
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["response"]
        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_body = e.response.text
            except Exception:
                pass
            raise LLMError(
                f"Failed to analyze image (HTTP {e.response.status_code}): {error_body or str(e)}",
                {"status_code": e.response.status_code, "model": model},
            )
        except httpx.RequestError as e:
            raise ServiceUnavailableError(
                f"Ollama service unreachable at {self.base_url}: {type(e).__name__}: {str(e)}"
            )

    async def health_check(self) -> bool:
        """Check if Ollama connection is healthy.

        Returns:
            True if Ollama is accessible, False otherwise
        """
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.base_url}/api/tags",
                timeout=httpx.Timeout(5.0),
            )
            return response.status_code == 200
        except Exception:
            return False

