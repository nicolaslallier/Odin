"""Unit tests for Ollama LLM service.

This module tests the Ollama service client for LLM operations,
model management, and text generation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.services.ollama import OllamaService


class TestOllamaService:
    """Test suite for OllamaService."""

    @pytest.fixture
    def ollama_service(self) -> OllamaService:
        """Create an OllamaService instance."""
        return OllamaService(base_url="http://ollama:11434")

    def test_ollama_service_initialization(self) -> None:
        """Test that OllamaService initializes with base URL."""
        service = OllamaService(base_url="http://localhost:11434")
        assert service.base_url == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_list_models_success(self, ollama_service: OllamaService) -> None:
        """Test list_models returns available models."""
        with patch("src.api.services.ollama.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={
                "models": [{"name": "llama2"}, {"name": "codellama"}]
            })
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await ollama_service.list_models()
            
            assert result == [{"name": "llama2"}, {"name": "codellama"}]
            mock_client.get.assert_called_once_with(f"{ollama_service.base_url}/api/tags")

    @pytest.mark.asyncio
    async def test_generate_text_success(self, ollama_service: OllamaService) -> None:
        """Test generate_text returns generated text."""
        with patch("src.api.services.ollama.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={"response": "Generated text"})
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await ollama_service.generate_text("llama2", "Hello")
            
            assert result == "Generated text"
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == f"{ollama_service.base_url}/api/generate"
            assert call_args[1]["json"]["model"] == "llama2"
            assert call_args[1]["json"]["prompt"] == "Hello"

    @pytest.mark.asyncio
    async def test_generate_text_with_system_prompt(self, ollama_service: OllamaService) -> None:
        """Test generate_text with system prompt."""
        with patch("src.api.services.ollama.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={"response": "Generated text"})
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await ollama_service.generate_text(
                "llama2", "Hello", system="You are helpful"
            )
            
            assert result == "Generated text"
            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["system"] == "You are helpful"

    @pytest.mark.asyncio
    async def test_generate_text_streaming(self, ollama_service: OllamaService) -> None:
        """Test generate_text with streaming enabled."""
        with patch("src.api.services.ollama.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            
            # Mock aiter_lines as an async generator
            async def mock_aiter_lines():
                for line in ['{"response": "Hello"}', '{"response": " World"}']:
                    yield line
            
            mock_response.aiter_lines = mock_aiter_lines
            
            # Mock the stream context manager
            mock_stream_cm = AsyncMock()
            mock_stream_cm.__aenter__.return_value = mock_response
            mock_stream_cm.__aexit__.return_value = None
            mock_client.stream = MagicMock(return_value=mock_stream_cm)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            chunks = []
            async for chunk in ollama_service.generate_text_streaming("llama2", "Hello"):
                chunks.append(chunk)
            
            assert chunks == ["Hello", " World"]

    @pytest.mark.asyncio
    async def test_pull_model_success(self, ollama_service: OllamaService) -> None:
        """Test pull_model downloads a model."""
        with patch("src.api.services.ollama.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={"status": "success"})
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await ollama_service.pull_model("llama2")
            
            assert result is True
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == f"{ollama_service.base_url}/api/pull"
            assert call_args[1]["json"]["name"] == "llama2"

    @pytest.mark.asyncio
    async def test_delete_model_success(self, ollama_service: OllamaService) -> None:
        """Test delete_model removes a model."""
        with patch("src.api.services.ollama.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.delete.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await ollama_service.delete_model("llama2")
            
            assert result is True
            mock_client.delete.assert_called_once()
            call_args = mock_client.delete.call_args
            assert call_args[0][0] == f"{ollama_service.base_url}/api/delete"

    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama_service: OllamaService) -> None:
        """Test health check returns True when Ollama is accessible."""
        with patch("src.api.services.ollama.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await ollama_service.health_check()
            
            assert result is True
            mock_client.get.assert_called_once_with(f"{ollama_service.base_url}/api/tags", timeout=5.0)

    @pytest.mark.asyncio
    async def test_health_check_failure(self, ollama_service: OllamaService) -> None:
        """Test health check returns False when Ollama is not accessible."""
        with patch("src.api.services.ollama.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection failed")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await ollama_service.health_check()
            
            assert result is False

