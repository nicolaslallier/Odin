"""Unit tests for image analysis routes.

This module tests the image analysis API endpoints with comprehensive coverage
of success cases, error handling, and edge cases.
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.domain.entities import ImageAnalysis
from src.api.exceptions import LLMError, ResourceNotFoundError, StorageError, ValidationError
from src.api.routes.image_analysis import router


@pytest.fixture
def mock_image_analysis_service() -> Mock:
    """Create a mock ImageAnalysisService for testing.

    Returns:
        Mock image analysis service
    """
    service = Mock()

    sample_analysis = ImageAnalysis(
        id=1,
        filename="test.jpg",
        bucket="images",
        object_key="test_123456.jpg",
        content_type="image/jpeg",
        size_bytes=1024,
        llm_description="A beautiful sunset over mountains",
        model_used="llava:latest",
    )

    service.analyze_and_store = AsyncMock(return_value=sample_analysis)
    service.get_analysis = AsyncMock(return_value=sample_analysis)
    service.list_analyses = AsyncMock(return_value=[sample_analysis])
    service.delete_analysis = AsyncMock()

    return service


@pytest.fixture
def mock_container(mock_image_analysis_service: Mock) -> Mock:
    """Create a mock ServiceContainer for testing.

    Args:
        mock_image_analysis_service: Mock image analysis service

    Returns:
        Mock container
    """
    container = Mock()
    container.image_analysis = mock_image_analysis_service
    return container


@pytest.fixture
def app(mock_container: Mock) -> FastAPI:
    """Create a FastAPI test application.

    Args:
        mock_container: Mock service container

    Returns:
        FastAPI application instance
    """
    app = FastAPI()
    app.include_router(router)
    app.state.container = mock_container
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client.

    Args:
        app: FastAPI application

    Returns:
        Test client instance
    """
    return TestClient(app)


@pytest.mark.unit
class TestAnalyzeImageEndpoint:
    """Test cases for POST /llm/analyze-image endpoint."""

    def test_analyze_image_success(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test successful image upload and analysis."""
        # Create test file
        file_content = b"fake_image_data"
        files = {"file": ("test.jpg", BytesIO(file_content), "image/jpeg")}
        data = {
            "prompt": "Describe this image",
            "model": "llava:latest",
        }

        response = client.post("/llm/analyze-image", files=files, data=data)

        assert response.status_code == 200
        result = response.json()
        assert result["id"] == 1
        assert result["filename"] == "test.jpg"
        assert result["llm_description"] == "A beautiful sunset over mountains"
        assert result["model_used"] == "llava:latest"
        assert "metadata" in result

        # Verify service was called
        mock_image_analysis_service.analyze_and_store.assert_called_once()

    def test_analyze_image_without_optional_params(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test image analysis with only required parameters."""
        file_content = b"fake_image_data"
        files = {"file": ("test.jpg", BytesIO(file_content), "image/jpeg")}

        response = client.post("/llm/analyze-image", files=files)

        assert response.status_code == 200

        # Verify service was called with defaults
        call_args = mock_image_analysis_service.analyze_and_store.call_args
        assert call_args[1]["prompt"] is None  # Will use default in service
        assert call_args[1]["model"] is None  # Will use default in service

    def test_analyze_image_png_format(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test analysis with PNG image."""
        file_content = b"fake_png_data"
        files = {"file": ("test.png", BytesIO(file_content), "image/png")}

        response = client.post("/llm/analyze-image", files=files)

        assert response.status_code == 200
        call_args = mock_image_analysis_service.analyze_and_store.call_args
        assert call_args[1]["content_type"] == "image/png"

    def test_analyze_image_validation_error(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test handling of validation errors."""
        mock_image_analysis_service.analyze_and_store.side_effect = ValidationError(
            "File too large"
        )

        file_content = b"fake_image_data"
        files = {"file": ("test.jpg", BytesIO(file_content), "image/jpeg")}

        response = client.post("/llm/analyze-image", files=files)

        assert response.status_code == 400
        assert "File too large" in response.json()["detail"]

    def test_analyze_image_storage_error(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test handling of storage errors."""
        mock_image_analysis_service.analyze_and_store.side_effect = StorageError("Upload failed")

        file_content = b"fake_image_data"
        files = {"file": ("test.jpg", BytesIO(file_content), "image/jpeg")}

        response = client.post("/llm/analyze-image", files=files)

        assert response.status_code == 500
        assert "Upload failed" in response.json()["detail"]

    def test_analyze_image_llm_error(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test handling of LLM errors."""
        mock_image_analysis_service.analyze_and_store.side_effect = LLMError("Model not available")

        file_content = b"fake_image_data"
        files = {"file": ("test.jpg", BytesIO(file_content), "image/jpeg")}

        response = client.post("/llm/analyze-image", files=files)

        assert response.status_code == 500
        assert "Model not available" in response.json()["detail"]

    def test_analyze_image_missing_file(self, client: TestClient) -> None:
        """Test endpoint with missing file parameter."""
        data = {"prompt": "Describe this image"}

        response = client.post("/llm/analyze-image", data=data)

        assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.unit
class TestGetAnalysisEndpoint:
    """Test cases for GET /llm/analyze-image/{image_id} endpoint."""

    def test_get_analysis_success(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test successful retrieval of image analysis."""
        response = client.get("/llm/analyze-image/1")

        assert response.status_code == 200
        result = response.json()
        assert result["id"] == 1
        assert result["filename"] == "test.jpg"
        assert result["llm_description"] == "A beautiful sunset over mountains"

        mock_image_analysis_service.get_analysis.assert_called_once_with(1)

    def test_get_analysis_not_found(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test retrieval of non-existent analysis."""
        mock_image_analysis_service.get_analysis.side_effect = ResourceNotFoundError("Not found")

        response = client.get("/llm/analyze-image/999")

        assert response.status_code == 404
        assert "Not found" in response.json()["detail"]

    def test_get_analysis_invalid_id(self, client: TestClient) -> None:
        """Test endpoint with invalid ID parameter."""
        response = client.get("/llm/analyze-image/invalid")

        assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.unit
class TestListAnalysesEndpoint:
    """Test cases for GET /llm/analyze-image endpoint."""

    def test_list_analyses_success(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test successful listing of all analyses."""
        response = client.get("/llm/analyze-image")

        assert response.status_code == 200
        result = response.json()
        assert "analyses" in result
        assert "total" in result
        assert len(result["analyses"]) == 1
        assert result["total"] == 1
        assert result["analyses"][0]["id"] == 1

        mock_image_analysis_service.list_analyses.assert_called_once()

    def test_list_analyses_empty(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test listing when no analyses exist."""
        mock_image_analysis_service.list_analyses.return_value = []

        response = client.get("/llm/analyze-image")

        assert response.status_code == 200
        result = response.json()
        assert len(result["analyses"]) == 0
        assert result["total"] == 0


@pytest.mark.unit
class TestDeleteAnalysisEndpoint:
    """Test cases for DELETE /llm/analyze-image/{image_id} endpoint."""

    def test_delete_analysis_success(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test successful deletion of image analysis."""
        response = client.delete("/llm/analyze-image/1")

        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert "deleted" in result["message"].lower()

        mock_image_analysis_service.delete_analysis.assert_called_once_with(1)

    def test_delete_analysis_not_found(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test deletion of non-existent analysis."""
        mock_image_analysis_service.delete_analysis.side_effect = ResourceNotFoundError("Not found")

        response = client.delete("/llm/analyze-image/999")

        assert response.status_code == 404
        assert "Not found" in response.json()["detail"]

    def test_delete_analysis_invalid_id(self, client: TestClient) -> None:
        """Test endpoint with invalid ID parameter."""
        response = client.delete("/llm/analyze-image/invalid")

        assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.unit
class TestResponseFormats:
    """Test cases for response data formats."""

    def test_analysis_response_format(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test that response follows expected schema."""
        response = client.get("/llm/analyze-image/1")

        assert response.status_code == 200
        result = response.json()

        # Check required fields
        required_fields = [
            "id",
            "filename",
            "llm_description",
            "model_used",
            "metadata",
            "created_at",
            "updated_at",
        ]
        for field in required_fields:
            assert field in result

        # Check metadata structure
        metadata = result["metadata"]
        metadata_fields = ["bucket", "object_key", "content_type", "size_bytes"]
        for field in metadata_fields:
            assert field in metadata

    def test_list_response_format(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test that list response follows expected schema."""
        response = client.get("/llm/analyze-image")

        assert response.status_code == 200
        result = response.json()

        # Check required fields
        assert "analyses" in result
        assert "total" in result
        assert isinstance(result["analyses"], list)
        assert isinstance(result["total"], int)


@pytest.mark.unit
class TestErrorHandling:
    """Test cases for comprehensive error handling."""

    def test_generic_exception_handling(
        self, client: TestClient, mock_image_analysis_service: Mock
    ) -> None:
        """Test handling of unexpected exceptions."""
        mock_image_analysis_service.get_analysis.side_effect = Exception("Unexpected error")

        response = client.get("/llm/analyze-image/1")

        assert response.status_code == 500
        assert "detail" in response.json()

    def test_multiple_files_uploaded(self, client: TestClient) -> None:
        """Test endpoint behavior with multiple files (should handle first)."""
        file1 = ("test1.jpg", BytesIO(b"data1"), "image/jpeg")
        file2 = ("test2.jpg", BytesIO(b"data2"), "image/jpeg")
        files = [("file", file1), ("file", file2)]

        # FastAPI should only accept one file with the 'file' parameter
        response = client.post("/llm/analyze-image", files=files)

        # Should succeed with first file or return validation error
        assert response.status_code in [200, 422]
