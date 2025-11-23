"""Unit tests for API schemas (pydantic models).

This module tests the pydantic models used for API requests and responses.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.models.schemas import (
    CircuitBreakerState,
    CircuitBreakerStates,
    DataItem,
    DataListResponse,
    FileListResponse,
    FileUploadResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    ImageAnalysisListResponse,
    ImageAnalysisResponse,
    ImageMetadata,
    LogAnalysisRequest,
    LogAnalysisResponse,
    LogEntry,
    LogListResponse,
    LogSearchRequest,
    LogStatistics,
    LogStatisticsByLevel,
    MessageRequest,
    MessageResponse,
    ModelInfo,
    ModelListResponse,
    SecretRequest,
    SecretResponse,
    ServiceHealthResponse,
)


@pytest.mark.unit
class TestHealthModels:
    """Test health check models."""

    def test_health_response(self) -> None:
        """Test HealthResponse model."""
        health = HealthResponse(status="healthy", service="odin-api")
        assert health.status == "healthy"
        assert health.service == "odin-api"

    def test_service_health_response(self) -> None:
        """Test ServiceHealthResponse model."""
        health = ServiceHealthResponse(
            database=True,
            storage=True,
            queue=True,
            vault=True,
            ollama=False,
        )
        assert health.database is True
        assert health.ollama is False


@pytest.mark.unit
class TestFileModels:
    """Test file operation models."""

    def test_file_upload_response(self) -> None:
        """Test FileUploadResponse model."""
        response = FileUploadResponse(
            bucket="test-bucket",
            key="test.txt",
            message="File uploaded",
        )
        assert response.bucket == "test-bucket"
        assert response.key == "test.txt"

    def test_file_list_response(self) -> None:
        """Test FileListResponse model."""
        response = FileListResponse(
            bucket="test-bucket",
            files=["file1.txt", "file2.txt"],
        )
        assert response.bucket == "test-bucket"
        assert len(response.files) == 2


@pytest.mark.unit
class TestMessageModels:
    """Test message queue models."""

    def test_message_request(self) -> None:
        """Test MessageRequest model."""
        request = MessageRequest(queue="test-queue", message="test message")
        assert request.queue == "test-queue"
        assert request.message == "test message"

    def test_message_response(self) -> None:
        """Test MessageResponse model."""
        response = MessageResponse(queue="test-queue", message="test message")
        assert response.queue == "test-queue"
        assert response.message == "test message"

    def test_message_response_none(self) -> None:
        """Test MessageResponse with None message."""
        response = MessageResponse(queue="test-queue", message=None)
        assert response.message is None


@pytest.mark.unit
class TestSecretModels:
    """Test secret management models."""

    def test_secret_request(self) -> None:
        """Test SecretRequest model."""
        request = SecretRequest(
            path="myapp/secret",
            data={"key": "value"},
        )
        assert request.path == "myapp/secret"
        assert request.data == {"key": "value"}

    def test_secret_response(self) -> None:
        """Test SecretResponse model."""
        response = SecretResponse(
            path="myapp/secret",
            data={"key": "value"},
        )
        assert response.path == "myapp/secret"
        assert response.data == {"key": "value"}


@pytest.mark.unit
class TestLLMModels:
    """Test LLM operation models."""

    def test_generate_request(self) -> None:
        """Test GenerateRequest model."""
        request = GenerateRequest(
            model="llama2",
            prompt="Test prompt",
            system="System prompt",
        )
        assert request.model == "llama2"
        assert request.prompt == "Test prompt"
        assert request.system == "System prompt"

    def test_generate_request_no_system(self) -> None:
        """Test GenerateRequest without system prompt."""
        request = GenerateRequest(model="llama2", prompt="Test prompt")
        assert request.system is None

    def test_generate_response(self) -> None:
        """Test GenerateResponse model."""
        response = GenerateResponse(model="llama2", response="Generated text")
        assert response.model == "llama2"
        assert response.response == "Generated text"

    def test_model_info(self) -> None:
        """Test ModelInfo model."""
        model = ModelInfo(
            name="llama2",
            size=1234567890,
            digest="abc123",
            modified_at="2024-01-01T00:00:00Z",
        )
        assert model.name == "llama2"
        assert model.size == 1234567890

    def test_model_list_response(self) -> None:
        """Test ModelListResponse model."""
        model1 = ModelInfo(name="llama2")
        model2 = ModelInfo(name="mistral")
        response = ModelListResponse(models=[model1, model2])
        assert len(response.models) == 2


@pytest.mark.unit
class TestCircuitBreakerModels:
    """Test circuit breaker models."""

    def test_circuit_breaker_state(self) -> None:
        """Test CircuitBreakerState model."""
        state = CircuitBreakerState(
            name="database",
            state="closed",
            failure_count=0,
        )
        assert state.name == "database"
        assert state.state == "closed"

    def test_circuit_breaker_states(self) -> None:
        """Test CircuitBreakerStates model."""
        states = CircuitBreakerStates(breakers={"database": "closed", "storage": "open"})
        assert states.breakers["database"] == "closed"


@pytest.mark.unit
class TestDataModels:
    """Test data CRUD models."""

    def test_data_item(self) -> None:
        """Test DataItem model."""
        item = DataItem(
            id=1,
            name="Test Item",
            description="Test description",
            data={"key": "value"},
        )
        assert item.id == 1
        assert item.name == "Test Item"

    def test_data_item_defaults(self) -> None:
        """Test DataItem with default values."""
        item = DataItem(name="Test")
        assert item.id is None
        assert item.description is None
        assert item.data == {}

    def test_data_item_missing_name(self) -> None:
        """Test DataItem validation fails without name."""
        with pytest.raises(ValidationError):
            DataItem()

    def test_data_list_response(self) -> None:
        """Test DataListResponse model."""
        item1 = DataItem(id=1, name="Item1")
        item2 = DataItem(id=2, name="Item2")
        response = DataListResponse(items=[item1, item2], total=2)
        assert len(response.items) == 2
        assert response.total == 2


@pytest.mark.unit
class TestLogModels:
    """Test log management models."""

    def test_log_entry(self) -> None:
        """Test LogEntry model."""
        log = LogEntry(
            id=1,
            timestamp="2024-01-01T00:00:00Z",
            level="INFO",
            service="api",
            logger="test.logger",
            message="Test message",
            module="test_module",
            function="test_function",
            line=42,
            exception=None,
            request_id="req-123",
            task_id=None,
            user_id=None,
            metadata={},
            created_at="2024-01-01T00:00:00Z",
        )
        assert log.id == 1
        assert log.level == "INFO"

    def test_log_list_response(self) -> None:
        """Test LogListResponse model."""
        log1 = LogEntry(
            id=1,
            timestamp="2024-01-01T00:00:00Z",
            level="INFO",
            service="api",
            message="Test 1",
            created_at="2024-01-01T00:00:00Z",
        )
        response = LogListResponse(logs=[log1], total=1, limit=100, offset=0)
        assert len(response.logs) == 1
        assert response.total == 1

    def test_log_search_request(self) -> None:
        """Test LogSearchRequest model."""
        request = LogSearchRequest(
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-02T00:00:00Z",
            level="ERROR",
            service="api",
            search="test",
            limit=50,
            offset=0,
        )
        assert request.level == "ERROR"
        assert request.limit == 50

    def test_log_search_request_defaults(self) -> None:
        """Test LogSearchRequest with defaults."""
        request = LogSearchRequest()
        assert request.limit == 100
        assert request.offset == 0

    def test_log_statistics_by_level(self) -> None:
        """Test LogStatisticsByLevel model."""
        stats = LogStatisticsByLevel(
            DEBUG=10,
            INFO=50,
            WARNING=20,
            ERROR=5,
            CRITICAL=1,
        )
        assert stats.DEBUG == 10
        assert stats.INFO == 50

    def test_log_statistics(self) -> None:
        """Test LogStatistics model."""
        by_level = LogStatisticsByLevel(INFO=100, ERROR=10)
        stats = LogStatistics(
            time_range={"start": "2024-01-01", "end": "2024-01-02"},
            total_logs=110,
            by_level=by_level,
            by_service={"api": {"INFO": 50, "ERROR": 5}},
        )
        assert stats.total_logs == 110

    def test_log_analysis_request(self) -> None:
        """Test LogAnalysisRequest model."""
        request = LogAnalysisRequest(
            log_ids=[1, 2, 3],
            analysis_type="root_cause",
            max_logs=50,
        )
        assert request.log_ids == [1, 2, 3]
        assert request.max_logs == 50

    def test_log_analysis_response(self) -> None:
        """Test LogAnalysisResponse model."""
        response = LogAnalysisResponse(
            analysis_type="root_cause",
            logs_analyzed=10,
            summary="Test summary",
            findings=["Finding 1", "Finding 2"],
            recommendations=["Recommendation 1"],
            patterns=[{"pattern": "error_pattern"}],
            related_logs=[1, 2, 3],
        )
        assert response.logs_analyzed == 10
        assert len(response.findings) == 2


@pytest.mark.unit
class TestImageModels:
    """Test image analysis models."""

    def test_image_metadata(self) -> None:
        """Test ImageMetadata model."""
        metadata = ImageMetadata(
            bucket="images",
            object_key="test.jpg",
            content_type="image/jpeg",
            size_bytes=1024,
        )
        assert metadata.bucket == "images"
        assert metadata.size_bytes == 1024

    def test_image_analysis_response(self) -> None:
        """Test ImageAnalysisResponse model."""
        metadata = ImageMetadata(
            bucket="images",
            object_key="test.jpg",
            content_type="image/jpeg",
            size_bytes=1024,
        )
        response = ImageAnalysisResponse(
            id=1,
            filename="test.jpg",
            llm_description="A test image",
            model_used="llava:latest",
            metadata=metadata,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        assert response.id == 1
        assert response.llm_description == "A test image"

    def test_image_analysis_list_response(self) -> None:
        """Test ImageAnalysisListResponse model."""
        metadata = ImageMetadata(
            bucket="images",
            object_key="test.jpg",
            content_type="image/jpeg",
            size_bytes=1024,
        )
        analysis = ImageAnalysisResponse(
            id=1,
            filename="test.jpg",
            metadata=metadata,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        response = ImageAnalysisListResponse(analyses=[analysis], total=1)
        assert len(response.analyses) == 1
        assert response.total == 1
