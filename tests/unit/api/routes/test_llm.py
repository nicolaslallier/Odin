"""Unit tests for LLM routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.config import APIConfig
from src.api.routes.llm import router


class TestLLMRoutes:
    """Test suite for LLM routes."""

    @pytest.fixture
    def mock_config(self) -> APIConfig:
        """Create a mock configuration."""
        return APIConfig(
            host="0.0.0.0",
            port=8001,
            postgres_dsn="postgresql://test:test@localhost:5432/test",
            minio_endpoint="minio:9000",
            minio_access_key="minioadmin",
            minio_secret_key="minioadmin",
            rabbitmq_url="amqp://test:test@localhost:5672/",
            vault_addr="http://vault:8200",
            vault_token="test-token",
            ollama_base_url="http://ollama:11434",
        )

    @pytest.fixture
    def app(self, mock_config: APIConfig) -> FastAPI:
        """Create a test FastAPI app."""
        app = FastAPI()
        app.state.config = mock_config
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    def test_list_models_success(self, client: TestClient, app: FastAPI) -> None:
        """Test model listing endpoint."""
        from src.api.routes.llm import get_ollama_service
        
        mock_ollama = AsyncMock()
        mock_ollama.list_models = AsyncMock(return_value=[{"name": "llama2"}])
        
        app.dependency_overrides[get_ollama_service] = lambda: mock_ollama
        
        try:
            response = client.get("/llm/models")
            
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_generate_text_success(self, client: TestClient, app: FastAPI) -> None:
        """Test text generation endpoint."""
        from src.api.routes.llm import get_ollama_service
        
        mock_ollama = AsyncMock()
        mock_ollama.generate_text = AsyncMock(return_value="Generated text")
        
        app.dependency_overrides[get_ollama_service] = lambda: mock_ollama
        
        try:
            response = client.post(
                "/llm/generate",
                json={"model": "llama2", "prompt": "Hello"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["response"] == "Generated text"
        finally:
            app.dependency_overrides.clear()

    def test_list_models_error(self, client: TestClient, app: FastAPI) -> None:
        """Test model listing with error."""
        from src.api.routes.llm import get_ollama_service
        
        mock_ollama = AsyncMock()
        mock_ollama.list_models = AsyncMock(side_effect=Exception("Connection error"))
        
        app.dependency_overrides[get_ollama_service] = lambda: mock_ollama
        
        try:
            response = client.get("/llm/models")
            
            assert response.status_code == 500
            assert "Connection error" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_generate_text_error(self, client: TestClient, app: FastAPI) -> None:
        """Test text generation with error."""
        from src.api.routes.llm import get_ollama_service
        
        mock_ollama = AsyncMock()
        mock_ollama.generate_text = AsyncMock(side_effect=Exception("Generation error"))
        
        app.dependency_overrides[get_ollama_service] = lambda: mock_ollama
        
        try:
            response = client.post(
                "/llm/generate",
                json={"model": "llama2", "prompt": "Hello"},
            )
            
            assert response.status_code == 500
            assert "Generation error" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

