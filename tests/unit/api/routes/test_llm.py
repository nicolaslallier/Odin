"""Unit tests for LLM routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.llm import router


class TestLLMRoutes:
    """Test suite for LLM routes."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create a test FastAPI app."""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    def test_list_models_success(self, client: TestClient) -> None:
        """Test model listing endpoint."""
        with patch("src.api.routes.llm.get_ollama_service") as mock_service:
            mock_ollama = AsyncMock()
            mock_ollama.list_models.return_value = [{"name": "llama2"}]
            mock_service.return_value = mock_ollama
            
            response = client.get("/llm/models")
            
            assert response.status_code == 200

    def test_generate_text_success(self, client: TestClient) -> None:
        """Test text generation endpoint."""
        with patch("src.api.routes.llm.get_ollama_service") as mock_service:
            mock_ollama = AsyncMock()
            mock_ollama.generate_text.return_value = "Generated text"
            mock_service.return_value = mock_ollama
            
            response = client.post(
                "/llm/generate",
                json={"model": "llama2", "prompt": "Hello"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["response"] == "Generated text"

