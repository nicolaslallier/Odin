"""Unit tests for Ollama LLM service.

This module tests the Ollama service client for LLM operations,
model management, and text generation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.services.ollama import OllamaService


class TestOllamaService:
    """Test suite for OllamaService."""

    @pytest.fixture
    def ollama_service(self) -> OllamaService:
        """Create an OllamaService instance with mocked client."""
        service = OllamaService(base_url="http://ollama:11434")
        # Mock the HTTP client directly to avoid needing real initialization
        service._client = AsyncMock()
        return service

    def test_ollama_service_initialization(self) -> None:
        """Test that OllamaService initializes with base URL."""
        service = OllamaService(base_url="http://localhost:11434")
        assert service.base_url == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_list_models_success(self, ollama_service: OllamaService) -> None:
        """Test list_models returns available models."""
        # Mock the get method on the initialized client
        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={"models": [{"name": "llama2"}, {"name": "codellama"}]}
        )
        mock_response.raise_for_status = MagicMock()
        ollama_service._client.get = AsyncMock(return_value=mock_response)

        result = await ollama_service.list_models()

        assert len(result) == 2
        assert result[0]["name"] == "llama2"
        assert result[1]["name"] == "codellama"
        ollama_service._client.get.assert_called_once_with(f"{ollama_service.base_url}/api/tags")

    @pytest.mark.asyncio
    async def test_generate_text_success(self, ollama_service: OllamaService) -> None:
        """Test generate_text returns generated text."""
        # Mock the post method on the initialized client
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"response": "Generated text"})
        mock_response.raise_for_status = MagicMock()
        ollama_service._client.post = AsyncMock(return_value=mock_response)

        result = await ollama_service.generate_text("llama2", "Hello")

        assert result == "Generated text"
        ollama_service._client.post.assert_called_once()
        call_args = ollama_service._client.post.call_args
        assert call_args[0][0] == f"{ollama_service.base_url}/api/generate"
        assert call_args[1]["json"]["model"] == "llama2"
        assert call_args[1]["json"]["prompt"] == "Hello"

    @pytest.mark.asyncio
    async def test_generate_text_with_system_prompt(self, ollama_service: OllamaService) -> None:
        """Test generate_text with system prompt."""
        # Mock the post method on the initialized client
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"response": "Generated text"})
        mock_response.raise_for_status = MagicMock()
        ollama_service._client.post = AsyncMock(return_value=mock_response)

        result = await ollama_service.generate_text("llama2", "Hello", system="You are helpful")

        assert result == "Generated text"
        call_args = ollama_service._client.post.call_args
        assert call_args[1]["json"]["system"] == "You are helpful"

    @pytest.mark.asyncio
    async def test_generate_text_streaming(self, ollama_service: OllamaService) -> None:
        """Test generate_text with streaming enabled."""

        # Mock aiter_lines as an async generator
        async def mock_aiter_lines():
            for line in ['{"response": "Hello"}', '{"response": " World"}']:
                yield line

        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines

        # Mock the stream context manager
        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__.return_value = mock_response
        mock_stream_cm.__aexit__.return_value = None
        ollama_service._client.stream = MagicMock(return_value=mock_stream_cm)

        chunks = []
        async for chunk in ollama_service.generate_text_streaming("llama2", "Hello"):
            chunks.append(chunk)

        assert chunks == ["Hello", " World"]

    @pytest.mark.asyncio
    async def test_pull_model_success(self, ollama_service: OllamaService) -> None:
        """Test pull_model downloads a model."""
        # Mock the post method on the initialized client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"status": "success"})
        mock_response.raise_for_status = MagicMock()
        ollama_service._client.post = AsyncMock(return_value=mock_response)

        result = await ollama_service.pull_model("llama2")

        assert result is True
        ollama_service._client.post.assert_called_once()
        call_args = ollama_service._client.post.call_args
        assert call_args[0][0] == f"{ollama_service.base_url}/api/pull"
        assert call_args[1]["json"]["name"] == "llama2"

    @pytest.mark.asyncio
    async def test_delete_model_success(self, ollama_service: OllamaService) -> None:
        """Test delete_model removes a model."""
        # Mock the delete method on the initialized client
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        ollama_service._client.delete = AsyncMock(return_value=mock_response)

        result = await ollama_service.delete_model("llama2")

        assert result is True
        ollama_service._client.delete.assert_called_once()
        call_args = ollama_service._client.delete.call_args
        assert call_args[0][0] == f"{ollama_service.base_url}/api/delete"

    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama_service: OllamaService) -> None:
        """Test health check returns True when Ollama is accessible."""
        # Mock the get method on the initialized client
        mock_response = MagicMock()
        mock_response.status_code = 200
        ollama_service._client.get = AsyncMock(return_value=mock_response)

        result = await ollama_service.health_check()

        assert result is True
        ollama_service._client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, ollama_service: OllamaService) -> None:
        """Test health check returns False when Ollama is not accessible."""
        # Mock the get method to raise an exception
        ollama_service._client.get = AsyncMock(side_effect=Exception("Connection failed"))

        result = await ollama_service.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_analyze_image_success(self, ollama_service: OllamaService) -> None:
        """Test analyze_image returns image analysis."""
        # Mock the post method on the initialized client
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"response": "A sunset over mountains"})
        mock_response.raise_for_status = MagicMock()
        ollama_service._client.post = AsyncMock(return_value=mock_response)

        # Create test image data
        image_data = b"fake_image_data"

        result = await ollama_service.analyze_image(
            model="llava:latest",
            prompt="Describe this image",
            image_data=image_data,
        )

        assert result == "A sunset over mountains"
        ollama_service._client.post.assert_called_once()
        call_args = ollama_service._client.post.call_args
        assert call_args[0][0] == f"{ollama_service.base_url}/api/generate"
        assert call_args[1]["json"]["model"] == "llava:latest"
        assert call_args[1]["json"]["prompt"] == "Describe this image"
        assert "images" in call_args[1]["json"]
        assert len(call_args[1]["json"]["images"]) == 1

    @pytest.mark.asyncio
    async def test_analyze_image_with_system_prompt(self, ollama_service: OllamaService) -> None:
        """Test analyze_image with system prompt."""
        # Mock the post method on the initialized client
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"response": "Analysis text"})
        mock_response.raise_for_status = MagicMock()
        ollama_service._client.post = AsyncMock(return_value=mock_response)

        image_data = b"fake_image_data"

        result = await ollama_service.analyze_image(
            model="llava:latest",
            prompt="What is in this image?",
            image_data=image_data,
            system="You are an expert image analyst",
        )

        assert result == "Analysis text"
        call_args = ollama_service._client.post.call_args
        assert call_args[1]["json"]["system"] == "You are an expert image analyst"

    @pytest.mark.asyncio
    async def test_analyze_image_base64_encoding(self, ollama_service: OllamaService) -> None:
        """Test that image data is properly base64 encoded."""
        # Mock the post method on the initialized client
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"response": "Image description"})
        mock_response.raise_for_status = MagicMock()
        ollama_service._client.post = AsyncMock(return_value=mock_response)

        # Use known bytes for predictable base64 output
        image_data = b"test"

        await ollama_service.analyze_image(
            model="llava:latest",
            prompt="Describe",
            image_data=image_data,
        )

        call_args = ollama_service._client.post.call_args
        images_array = call_args[1]["json"]["images"]
        assert len(images_array) == 1
        # Verify it's valid base64 string
        import base64

        try:
            decoded = base64.b64decode(images_array[0])
            assert decoded == image_data
        except Exception:
            pytest.fail("Image was not properly base64 encoded")

    @pytest.mark.asyncio
    async def test_analyze_image_http_error(self, ollama_service: OllamaService) -> None:
        """Test analyze_image handles HTTP errors properly."""
        from httpx import HTTPStatusError, Request, Response

        from src.api.exceptions import LLMError

        # Create a mock response for the exception
        mock_request = MagicMock(spec=Request)
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 500

        # Mock the post method to raise HTTPStatusError
        ollama_service._client.post = AsyncMock(
            side_effect=HTTPStatusError(
                "Server error", request=mock_request, response=mock_response
            )
        )

        image_data = b"test"

        with pytest.raises(LLMError, match="Failed to analyze image"):
            await ollama_service.analyze_image(
                model="llava:latest",
                prompt="Describe",
                image_data=image_data,
            )

    @pytest.mark.asyncio
    async def test_analyze_image_request_error(self, ollama_service: OllamaService) -> None:
        """Test analyze_image handles request errors properly."""
        from httpx import RequestError

        from src.api.exceptions import ServiceUnavailableError

        # Mock the post method to raise RequestError
        ollama_service._client.post = AsyncMock(side_effect=RequestError("Connection failed"))

        image_data = b"test"

        with pytest.raises(ServiceUnavailableError, match="Ollama service unreachable"):
            await ollama_service.analyze_image(
                model="llava:latest",
                prompt="Describe",
                image_data=image_data,
            )

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        svc = OllamaService(base_url="http://ollama:11434")
        await svc.initialize()
        client1 = svc._client
        await svc.initialize()  # Should not replace the client
        assert svc._client is client1

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        svc = OllamaService(base_url="http://ollama:11434")
        await svc.close()  # Should do nothing when client is None (no error)

    def test_get_client_not_initialized(self):
        svc = OllamaService(base_url="http://ollama:11434")
        with pytest.raises(Exception) as exc:
            svc._get_client()
        assert "not initialized" in str(exc.value)

    @pytest.mark.asyncio
    async def test_list_models_http_error(self, ollama_service):
        from httpx import HTTPStatusError, Request, Response

        from src.api.exceptions import LLMError

        mock_request = MagicMock(spec=Request)
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 500
        ollama_service._client.get = AsyncMock(
            side_effect=HTTPStatusError("fail", request=mock_request, response=mock_response)
        )
        with pytest.raises(LLMError, match="Failed to list models"):
            await ollama_service.list_models()

    @pytest.mark.asyncio
    async def test_list_models_request_error(self, ollama_service):
        from httpx import RequestError

        from src.api.exceptions import ServiceUnavailableError

        ollama_service._client.get = AsyncMock(side_effect=RequestError("bad connect"))
        with pytest.raises(ServiceUnavailableError, match="Ollama service unreachable"):
            await ollama_service.list_models()

    @pytest.mark.asyncio
    async def test_generate_text_http_error(self, ollama_service):
        from httpx import HTTPStatusError, Request, Response

        from src.api.exceptions import LLMError

        mock_request = MagicMock(spec=Request)
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 400
        ollama_service._client.post = AsyncMock(
            side_effect=HTTPStatusError("bad req", request=mock_request, response=mock_response)
        )
        with pytest.raises(LLMError, match="Failed to generate text"):
            await ollama_service.generate_text("llama2", "fail")

    @pytest.mark.asyncio
    async def test_generate_text_request_error(self, ollama_service):
        from httpx import RequestError

        from src.api.exceptions import ServiceUnavailableError

        ollama_service._client.post = AsyncMock(side_effect=RequestError("oops"))
        with pytest.raises(ServiceUnavailableError, match="Ollama service unreachable"):
            await ollama_service.generate_text("llama2", "fail")

    @pytest.mark.asyncio
    async def test_generate_text_streaming_http_error(self, ollama_service):
        from httpx import HTTPStatusError, Request, Response

        from src.api.exceptions import LLMError

        mock_request = MagicMock(spec=Request)
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 403
        cm = AsyncMock()
        cm.__aenter__.side_effect = HTTPStatusError(
            "forbidden", request=mock_request, response=mock_response
        )
        cm.__aexit__.return_value = None
        ollama_service._client.stream = MagicMock(return_value=cm)
        with pytest.raises(LLMError, match="Failed to generate streaming text"):
            async for _ in ollama_service.generate_text_streaming("model", "prompt"):
                pass

    @pytest.mark.asyncio
    async def test_generate_text_streaming_request_error(self, ollama_service):
        from httpx import RequestError

        from src.api.exceptions import ServiceUnavailableError

        cm = AsyncMock()
        cm.__aenter__.side_effect = RequestError("oops streaming")
        cm.__aexit__.return_value = None
        ollama_service._client.stream = MagicMock(return_value=cm)
        with pytest.raises(ServiceUnavailableError, match="Ollama service unreachable"):
            async for _ in ollama_service.generate_text_streaming("model", "prompt"):
                pass

    @pytest.mark.asyncio
    async def test_pull_model_http_error(self, ollama_service):
        from httpx import HTTPStatusError, Request, Response

        from src.api.exceptions import LLMError

        mock_request = MagicMock(spec=Request)
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 401
        ollama_service._client.post = AsyncMock(
            side_effect=HTTPStatusError("fail pull", request=mock_request, response=mock_response)
        )
        with pytest.raises(LLMError, match="Failed to pull model"):
            await ollama_service.pull_model("xx")

    @pytest.mark.asyncio
    async def test_pull_model_request_error(self, ollama_service):
        from httpx import RequestError

        from src.api.exceptions import ServiceUnavailableError

        ollama_service._client.post = AsyncMock(side_effect=RequestError("lost"))
        with pytest.raises(ServiceUnavailableError, match="Ollama service unreachable"):
            await ollama_service.pull_model("xx")

    @pytest.mark.asyncio
    async def test_delete_model_http_error(self, ollama_service):
        from httpx import HTTPStatusError, Request, Response

        from src.api.exceptions import LLMError

        mock_request = MagicMock(spec=Request)
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 410
        ollama_service._client.delete = AsyncMock(
            side_effect=HTTPStatusError("fail delete", request=mock_request, response=mock_response)
        )
        with pytest.raises(LLMError, match="Failed to delete model"):
            await ollama_service.delete_model("xx")

    @pytest.mark.asyncio
    async def test_delete_model_request_error(self, ollama_service):
        from httpx import RequestError

        from src.api.exceptions import ServiceUnavailableError

        ollama_service._client.delete = AsyncMock(side_effect=RequestError("gone"))
        with pytest.raises(ServiceUnavailableError, match="Ollama service unreachable"):
            await ollama_service.delete_model("xx")

    @pytest.mark.asyncio
    async def test_analyze_image_http_error_text_exception(self, ollama_service):
        # Simulate .response.text raising inside exception block
        from httpx import HTTPStatusError, Request, Response

        from src.api.exceptions import LLMError

        mock_request = MagicMock(spec=Request)
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 500
        type(mock_response).text = property(
            lambda self: (_ for _ in ()).throw(Exception("text fail"))
        )
        ollama_service._client.post = AsyncMock(
            side_effect=HTTPStatusError("server fail", request=mock_request, response=mock_response)
        )
        with pytest.raises(LLMError, match="Failed to analyze image"):
            await ollama_service.analyze_image(model="xx", prompt="y", image_data=b"x")

    @pytest.mark.asyncio
    async def test_close_multiple(self):
        svc = OllamaService(base_url="http://abc")
        await svc.initialize()
        await svc.close()
        await svc.close()
        assert svc._client is None
