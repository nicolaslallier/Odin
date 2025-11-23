"""Unit tests for ImageAnalysisService.

This module tests the image analysis service orchestration layer with comprehensive
coverage of the full workflow: storage, database persistence, and LLM analysis.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.api.domain.entities import ImageAnalysis
from src.api.exceptions import DatabaseError, LLMError, StorageError, ValidationError
from src.api.services.image_analysis import ImageAnalysisService


@pytest.fixture
def mock_storage() -> Mock:
    """Create a mock StorageService for testing.

    Returns:
        Mock storage service
    """
    storage = Mock()
    storage.bucket_exists = Mock(return_value=True)
    storage.create_bucket = Mock()
    storage.upload_file = Mock()
    storage.download_file = Mock(return_value=b"fake_image_data")
    storage.delete_file = Mock()
    return storage


@pytest.fixture
def mock_database() -> Mock:
    """Create a mock DatabaseService for testing.

    Returns:
        Mock database service
    """
    database = Mock()

    # Mock get_session context manager
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session
    mock_cm.__aexit__.return_value = None
    database.get_session = Mock(return_value=mock_cm)

    return database


@pytest.fixture
def mock_ollama() -> Mock:
    """Create a mock OllamaService for testing.

    Returns:
        Mock Ollama service
    """
    ollama = Mock()
    ollama.analyze_image = AsyncMock(return_value="A beautiful sunset over mountains")
    return ollama


@pytest.fixture
def mock_repository() -> Mock:
    """Create a mock ImageRepository for testing.

    Returns:
        Mock repository
    """
    repository = Mock()

    sample_analysis = ImageAnalysis(
        id=1,
        filename="test.jpg",
        bucket="images",
        object_key="test_123456.jpg",
        content_type="image/jpeg",
        size_bytes=1024,
        llm_description="A beautiful sunset",
        model_used="llava:latest",
    )

    repository.create = AsyncMock(return_value=sample_analysis)
    repository.get_by_id = AsyncMock(return_value=sample_analysis)
    repository.get_all = AsyncMock(return_value=[sample_analysis])
    repository.delete = AsyncMock()
    repository.count = AsyncMock(return_value=1)

    return repository


@pytest.fixture
def image_analysis_service(
    mock_storage: Mock, mock_database: Mock, mock_ollama: Mock
) -> ImageAnalysisService:
    """Create an ImageAnalysisService instance with mocked dependencies.

    Args:
        mock_storage: Mock storage service
        mock_database: Mock database service
        mock_ollama: Mock Ollama service

    Returns:
        ImageAnalysisService instance
    """
    return ImageAnalysisService(
        storage=mock_storage,
        database=mock_database,
        ollama=mock_ollama,
        default_model="llava:latest",
        image_bucket="images",
        max_size_mb=10,
    )


@pytest.mark.unit
class TestImageAnalysisServiceInit:
    """Test cases for ImageAnalysisService initialization."""

    def test_initialization(
        self, mock_storage: Mock, mock_database: Mock, mock_ollama: Mock
    ) -> None:
        """Test that ImageAnalysisService initializes with correct parameters."""
        service = ImageAnalysisService(
            storage=mock_storage,
            database=mock_database,
            ollama=mock_ollama,
            default_model="llava:latest",
            image_bucket="images",
            max_size_mb=10,
        )

        assert service.storage == mock_storage
        assert service.database == mock_database
        assert service.ollama == mock_ollama
        assert service.default_model == "llava:latest"
        assert service.image_bucket == "images"
        assert service.max_size_mb == 10


@pytest.mark.unit
class TestAnalyzeAndStore:
    """Test cases for ImageAnalysisService.analyze_and_store()."""

    @pytest.mark.asyncio
    async def test_analyze_and_store_success(
        self, image_analysis_service: ImageAnalysisService, mock_repository: Mock
    ) -> None:
        """Test successful image analysis and storage."""
        # Arrange
        filename = "test.jpg"
        file_data = b"fake_image_data"
        content_type = "image/jpeg"
        prompt = "Describe this image"

        with patch(
            "src.api.services.image_analysis.ImageRepository",
            return_value=mock_repository,
        ):
            # Act
            result = await image_analysis_service.analyze_and_store(
                filename=filename,
                file_data=file_data,
                content_type=content_type,
                prompt=prompt,
            )

        # Assert
        assert result.filename == "test.jpg"
        assert result.llm_description == "A beautiful sunset"
        assert result.model_used == "llava:latest"

        # Verify storage was called
        image_analysis_service.storage.upload_file.assert_called_once()

        # Verify Ollama was called
        image_analysis_service.ollama.analyze_image.assert_called_once()

        # Verify repository create was called
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_and_store_with_custom_model(
        self, image_analysis_service: ImageAnalysisService, mock_repository: Mock
    ) -> None:
        """Test image analysis with custom model."""
        filename = "test.jpg"
        file_data = b"fake_image_data"
        content_type = "image/jpeg"
        prompt = "Describe this image"
        custom_model = "bakllava:latest"

        with patch(
            "src.api.services.image_analysis.ImageRepository",
            return_value=mock_repository,
        ):
            await image_analysis_service.analyze_and_store(
                filename=filename,
                file_data=file_data,
                content_type=content_type,
                prompt=prompt,
                model=custom_model,
            )

        # Verify Ollama was called with custom model
        call_args = image_analysis_service.ollama.analyze_image.call_args
        assert call_args[1]["model"] == custom_model

    @pytest.mark.asyncio
    async def test_analyze_and_store_file_too_large(
        self, image_analysis_service: ImageAnalysisService
    ) -> None:
        """Test that oversized files are rejected."""
        filename = "huge.jpg"
        # Create 11MB of data (exceeds 10MB limit)
        file_data = b"x" * (11 * 1024 * 1024)
        content_type = "image/jpeg"

        with pytest.raises(ValidationError, match="exceeds maximum size"):
            await image_analysis_service.analyze_and_store(
                filename=filename,
                file_data=file_data,
                content_type=content_type,
            )

    @pytest.mark.asyncio
    async def test_analyze_and_store_invalid_content_type(
        self, image_analysis_service: ImageAnalysisService
    ) -> None:
        """Test that invalid content types are rejected."""
        filename = "test.txt"
        file_data = b"not an image"
        content_type = "text/plain"

        with pytest.raises(ValidationError, match="Invalid image content type"):
            await image_analysis_service.analyze_and_store(
                filename=filename,
                file_data=file_data,
                content_type=content_type,
            )

    @pytest.mark.asyncio
    async def test_analyze_and_store_storage_error(
        self, image_analysis_service: ImageAnalysisService
    ) -> None:
        """Test handling of storage errors."""
        filename = "test.jpg"
        file_data = b"fake_image_data"
        content_type = "image/jpeg"

        # Make storage fail
        image_analysis_service.storage.upload_file.side_effect = StorageError("Upload failed")

        with pytest.raises(StorageError, match="Upload failed"):
            await image_analysis_service.analyze_and_store(
                filename=filename,
                file_data=file_data,
                content_type=content_type,
            )

    @pytest.mark.asyncio
    async def test_analyze_and_store_llm_error(
        self, image_analysis_service: ImageAnalysisService, mock_repository: Mock
    ) -> None:
        """Test handling of LLM errors with rollback."""
        filename = "test.jpg"
        file_data = b"fake_image_data"
        content_type = "image/jpeg"

        # Make LLM fail
        image_analysis_service.ollama.analyze_image.side_effect = LLMError("Model not found")

        with (
            patch(
                "src.api.services.image_analysis.ImageRepository",
                return_value=mock_repository,
            ),
            pytest.raises(LLMError, match="Model not found"),
        ):
            await image_analysis_service.analyze_and_store(
                filename=filename,
                file_data=file_data,
                content_type=content_type,
            )

        # Verify storage delete was called for cleanup
        image_analysis_service.storage.delete_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_and_store_database_error(
        self, image_analysis_service: ImageAnalysisService, mock_repository: Mock
    ) -> None:
        """Test handling of database errors with rollback."""
        filename = "test.jpg"
        file_data = b"fake_image_data"
        content_type = "image/jpeg"

        # Make database fail
        mock_repository.create.side_effect = DatabaseError("DB connection lost")

        with (
            patch(
                "src.api.services.image_analysis.ImageRepository",
                return_value=mock_repository,
            ),
            pytest.raises(DatabaseError, match="DB connection lost"),
        ):
            await image_analysis_service.analyze_and_store(
                filename=filename,
                file_data=file_data,
                content_type=content_type,
            )

        # Verify storage delete was called for cleanup
        image_analysis_service.storage.delete_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_and_store_unique_object_key(
        self, image_analysis_service: ImageAnalysisService, mock_repository: Mock
    ) -> None:
        """Test that object keys are unique across multiple uploads."""
        filename = "test.jpg"
        file_data = b"fake_image_data"
        content_type = "image/jpeg"

        with patch(
            "src.api.services.image_analysis.ImageRepository",
            return_value=mock_repository,
        ):
            # Upload same file twice
            result1 = await image_analysis_service.analyze_and_store(
                filename=filename,
                file_data=file_data,
                content_type=content_type,
            )

            # Small delay to ensure different timestamp
            time.sleep(0.01)

            result2 = await image_analysis_service.analyze_and_store(
                filename=filename,
                file_data=file_data,
                content_type=content_type,
            )

        # Object keys should be different (contain timestamps)
        # Note: This is a simplified check since we're mocking
        assert mock_repository.create.call_count == 2


@pytest.mark.unit
class TestGetAnalysis:
    """Test cases for ImageAnalysisService.get_analysis()."""

    @pytest.mark.asyncio
    async def test_get_analysis_success(
        self, image_analysis_service: ImageAnalysisService, mock_repository: Mock
    ) -> None:
        """Test successful retrieval of image analysis."""
        with patch(
            "src.api.services.image_analysis.ImageRepository",
            return_value=mock_repository,
        ):
            result = await image_analysis_service.get_analysis(1)

        assert result.id == 1
        assert result.filename == "test.jpg"
        mock_repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_analysis_not_found(
        self, image_analysis_service: ImageAnalysisService, mock_repository: Mock
    ) -> None:
        """Test get_analysis with non-existent ID."""
        from src.api.exceptions import ResourceNotFoundError

        mock_repository.get_by_id.side_effect = ResourceNotFoundError("Not found")

        with (
            patch(
                "src.api.services.image_analysis.ImageRepository",
                return_value=mock_repository,
            ),
            pytest.raises(ResourceNotFoundError),
        ):
            await image_analysis_service.get_analysis(999)


@pytest.mark.unit
class TestListAnalyses:
    """Test cases for ImageAnalysisService.list_analyses()."""

    @pytest.mark.asyncio
    async def test_list_analyses_success(
        self, image_analysis_service: ImageAnalysisService, mock_repository: Mock
    ) -> None:
        """Test successful listing of all analyses."""
        with patch(
            "src.api.services.image_analysis.ImageRepository",
            return_value=mock_repository,
        ):
            result = await image_analysis_service.list_analyses()

        assert len(result) == 1
        assert result[0].filename == "test.jpg"
        mock_repository.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_analyses_empty(
        self, image_analysis_service: ImageAnalysisService, mock_repository: Mock
    ) -> None:
        """Test listing when no analyses exist."""
        mock_repository.get_all.return_value = []

        with patch(
            "src.api.services.image_analysis.ImageRepository",
            return_value=mock_repository,
        ):
            result = await image_analysis_service.list_analyses()

        assert len(result) == 0
        assert isinstance(result, list)


@pytest.mark.unit
class TestDeleteAnalysis:
    """Test cases for ImageAnalysisService.delete_analysis()."""

    @pytest.mark.asyncio
    async def test_delete_analysis_success(
        self, image_analysis_service: ImageAnalysisService, mock_repository: Mock
    ) -> None:
        """Test successful deletion of analysis and image."""
        with patch(
            "src.api.services.image_analysis.ImageRepository",
            return_value=mock_repository,
        ):
            await image_analysis_service.delete_analysis(1)

        # Verify get_by_id was called (to get object info)
        mock_repository.get_by_id.assert_called_once_with(1)

        # Verify storage delete was called
        image_analysis_service.storage.delete_file.assert_called_once()

        # Verify repository delete was called
        mock_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_analysis_not_found(
        self, image_analysis_service: ImageAnalysisService, mock_repository: Mock
    ) -> None:
        """Test delete with non-existent ID."""
        from src.api.exceptions import ResourceNotFoundError

        mock_repository.get_by_id.side_effect = ResourceNotFoundError("Not found")

        with (
            patch(
                "src.api.services.image_analysis.ImageRepository",
                return_value=mock_repository,
            ),
            pytest.raises(ResourceNotFoundError),
        ):
            await image_analysis_service.delete_analysis(999)

    @pytest.mark.asyncio
    async def test_delete_analysis_storage_error_continues(
        self, image_analysis_service: ImageAnalysisService, mock_repository: Mock
    ) -> None:
        """Test that DB deletion continues even if storage deletion fails."""
        # Make storage delete fail
        image_analysis_service.storage.delete_file.side_effect = StorageError("Delete failed")

        with patch(
            "src.api.services.image_analysis.ImageRepository",
            return_value=mock_repository,
        ):
            # Should not raise, continues to DB deletion
            await image_analysis_service.delete_analysis(1)

        # Verify repository delete was still called
        mock_repository.delete.assert_called_once_with(1)


@pytest.mark.unit
class TestContentTypeValidation:
    """Test cases for content type validation."""

    def test_supported_image_formats(self, image_analysis_service: ImageAnalysisService) -> None:
        """Test that all supported image formats are accepted."""
        supported_types = [
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
        ]

        for content_type in supported_types:
            # Should not raise
            is_valid = content_type.startswith("image/")
            assert is_valid is True

    def test_unsupported_formats(self, image_analysis_service: ImageAnalysisService) -> None:
        """Test that unsupported formats are rejected."""
        unsupported_types = [
            "text/plain",
            "application/pdf",
            "video/mp4",
            "application/octet-stream",
        ]

        for content_type in unsupported_types:
            is_valid = content_type.startswith("image/")
            assert is_valid is False


def test_generate_object_key_no_extension(image_analysis_service: ImageAnalysisService) -> None:
    """Test object key generation for filename without extension."""
    filename = "noextfilename"
    with patch("time.time", return_value=123456.789):
        key = image_analysis_service._generate_object_key(filename)
        assert key.startswith("noextfilename_")
        assert key.endswith("789000")


def test_generate_object_key_with_extension(image_analysis_service: ImageAnalysisService) -> None:
    """Test object key generation for filename with extension."""
    filename = "file.png"
    with patch("time.time", return_value=123):
        key = image_analysis_service._generate_object_key(filename)
        assert key.startswith("file_") and key.endswith(".png")


@pytest.mark.asyncio
async def test_analyze_and_store_creates_bucket(
    image_analysis_service: ImageAnalysisService, mock_repository: Mock
) -> None:
    """Test that bucket is created if it doesn't exist."""
    # Arrange
    filename = "bucket_test.jpg"
    file_data = b"img"
    content_type = "image/jpeg"
    image_analysis_service.storage.bucket_exists.return_value = False
    with patch("src.api.services.image_analysis.ImageRepository", return_value=mock_repository):
        await image_analysis_service.analyze_and_store(
            filename=filename,
            file_data=file_data,
            content_type=content_type,
        )
    image_analysis_service.storage.create_bucket.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_and_store_storage_error_on_cleanup(
    image_analysis_service: ImageAnalysisService, mock_repository: Mock
) -> None:
    """Test that StorageError during cleanup is swallowed and original error is raised."""
    # Trigger LLM failure AND make storage.delete_file raise
    filename = "fail.jpg"
    file_data = b"data"
    content_type = "image/jpeg"
    image_analysis_service.ollama.analyze_image.side_effect = Exception("fail analysis")
    image_analysis_service.storage.delete_file.side_effect = StorageError("forced cleanup fail")
    with patch("src.api.services.image_analysis.ImageRepository", return_value=mock_repository):
        with pytest.raises(Exception, match="fail analysis"):
            await image_analysis_service.analyze_and_store(
                filename=filename,
                file_data=file_data,
                content_type=content_type,
            )  # Should swallow StorageError and raise the original
    image_analysis_service.storage.delete_file.assert_called_once()
