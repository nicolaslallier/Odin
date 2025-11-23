"""Unit tests for ImageRepository.

This module tests the image analysis repository layer with comprehensive
coverage of CRUD operations and error handling.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.domain.entities import ImageAnalysis
from src.api.exceptions import DatabaseError, ResourceNotFoundError
from src.api.repositories.image_repository import ImageRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock AsyncSession for testing.

    Returns:
        Mock async session
    """
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def sample_image_entity() -> ImageAnalysis:
    """Create a sample ImageAnalysis entity for testing.

    Returns:
        Sample ImageAnalysis entity
    """
    return ImageAnalysis(
        filename="test.jpg",
        bucket="images",
        object_key="test_123456.jpg",
        content_type="image/jpeg",
        size_bytes=1024,
        llm_description="A test image",
        model_used="llava:latest",
    )


@pytest.mark.unit
class TestImageRepositoryCreate:
    """Test cases for ImageRepository.create()."""

    @pytest.mark.asyncio
    async def test_create_success(
        self, mock_session: AsyncMock, sample_image_entity: ImageAnalysis
    ) -> None:
        """Test successful image analysis record creation."""
        # Arrange
        repository = ImageRepository(mock_session)
        mock_result = Mock()
        mock_result.scalar_one.return_value = 1
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.create(sample_image_entity)

        # Assert
        assert result.id == 1
        assert result.filename == "test.jpg"
        assert result.bucket == "images"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_database_error(
        self, mock_session: AsyncMock, sample_image_entity: ImageAnalysis
    ) -> None:
        """Test create handles database errors properly."""
        # Arrange
        repository = ImageRepository(mock_session)
        mock_session.execute.side_effect = Exception("Database connection failed")

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to create image analysis"):
            await repository.create(sample_image_entity)
        mock_session.rollback.assert_called_once()


@pytest.mark.unit
class TestImageRepositoryGetById:
    """Test cases for ImageRepository.get_by_id()."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, mock_session: AsyncMock) -> None:
        """Test successful retrieval of image analysis by ID."""
        # Arrange
        repository = ImageRepository(mock_session)
        mock_row = Mock()
        mock_row.id = 1
        mock_row.filename = "test.jpg"
        mock_row.bucket = "images"
        mock_row.object_key = "test_123456.jpg"
        mock_row.content_type = "image/jpeg"
        mock_row.size_bytes = 1024
        mock_row.llm_description = "A test image"
        mock_row.model_used = "llava:latest"
        mock_row.created_at = datetime.utcnow()
        mock_row.updated_at = datetime.utcnow()

        mock_result = Mock()
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id(1)

        # Assert
        assert result.id == 1
        assert result.filename == "test.jpg"
        assert result.llm_description == "A test image"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_session: AsyncMock) -> None:
        """Test get_by_id raises ResourceNotFoundError when item doesn't exist."""
        # Arrange
        repository = ImageRepository(mock_session)
        mock_result = Mock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ResourceNotFoundError, match="Image analysis not found"):
            await repository.get_by_id(999)

    @pytest.mark.asyncio
    async def test_get_by_id_database_error(self, mock_session: AsyncMock) -> None:
        """Test get_by_id handles database errors properly."""
        # Arrange
        repository = ImageRepository(mock_session)
        mock_session.execute.side_effect = Exception("Query failed")

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to retrieve image analysis"):
            await repository.get_by_id(1)


@pytest.mark.unit
class TestImageRepositoryGetAll:
    """Test cases for ImageRepository.get_all()."""

    @pytest.mark.asyncio
    async def test_get_all_success(self, mock_session: AsyncMock) -> None:
        """Test successful retrieval of all image analyses."""
        # Arrange
        repository = ImageRepository(mock_session)
        mock_row1 = Mock()
        mock_row1.id = 1
        mock_row1.filename = "test1.jpg"
        mock_row1.bucket = "images"
        mock_row1.object_key = "test1_123456.jpg"
        mock_row1.content_type = "image/jpeg"
        mock_row1.size_bytes = 1024
        mock_row1.llm_description = "First image"
        mock_row1.model_used = "llava:latest"
        mock_row1.created_at = datetime.utcnow()
        mock_row1.updated_at = datetime.utcnow()

        mock_row2 = Mock()
        mock_row2.id = 2
        mock_row2.filename = "test2.png"
        mock_row2.bucket = "images"
        mock_row2.object_key = "test2_123457.png"
        mock_row2.content_type = "image/png"
        mock_row2.size_bytes = 2048
        mock_row2.llm_description = "Second image"
        mock_row2.model_used = "llava:latest"
        mock_row2.created_at = datetime.utcnow()
        mock_row2.updated_at = datetime.utcnow()

        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_all()

        # Assert
        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].id == 2
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_empty(self, mock_session: AsyncMock) -> None:
        """Test get_all returns empty list when no records exist."""
        # Arrange
        repository = ImageRepository(mock_session)
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_all()

        # Assert
        assert len(result) == 0
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_all_database_error(self, mock_session: AsyncMock) -> None:
        """Test get_all handles database errors properly."""
        # Arrange
        repository = ImageRepository(mock_session)
        mock_session.execute.side_effect = Exception("Query failed")

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to retrieve image analyses"):
            await repository.get_all()


@pytest.mark.unit
class TestImageRepositoryUpdate:
    """Test cases for ImageRepository.update()."""

    @pytest.mark.asyncio
    async def test_update_success(
        self, mock_session: AsyncMock, sample_image_entity: ImageAnalysis
    ) -> None:
        """Test successful update of image analysis record."""
        # Arrange
        repository = ImageRepository(mock_session)
        sample_image_entity.id = 1
        sample_image_entity.llm_description = "Updated description"

        # Mock get_by_id call
        mock_existing = Mock()
        mock_existing.first.return_value = Mock(id=1, filename="test.jpg", bucket="images")
        mock_session.execute.return_value = mock_existing

        # Act
        result = await repository.update(sample_image_entity)

        # Assert
        assert result.id == 1
        assert result.llm_description == "Updated description"
        assert mock_session.execute.call_count == 2  # get_by_id + update
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_without_id(
        self, mock_session: AsyncMock, sample_image_entity: ImageAnalysis
    ) -> None:
        """Test update fails when entity has no ID."""
        # Arrange
        repository = ImageRepository(mock_session)
        sample_image_entity.id = None

        # Act & Assert
        with pytest.raises(DatabaseError, match="Cannot update image analysis without ID"):
            await repository.update(sample_image_entity)

    @pytest.mark.asyncio
    async def test_update_not_found(
        self, mock_session: AsyncMock, sample_image_entity: ImageAnalysis
    ) -> None:
        """Test update fails when entity doesn't exist."""
        # Arrange
        repository = ImageRepository(mock_session)
        sample_image_entity.id = 999
        mock_result = Mock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ResourceNotFoundError):
            await repository.update(sample_image_entity)

    @pytest.mark.asyncio
    async def test_update_database_error(
        self, mock_session: AsyncMock, sample_image_entity: ImageAnalysis
    ) -> None:
        """Test update handles database errors properly."""
        # Arrange
        repository = ImageRepository(mock_session)
        sample_image_entity.id = 1

        # Mock get_by_id success, update fails
        mock_existing = Mock()
        mock_existing.first.return_value = Mock(id=1)
        mock_session.execute.side_effect = [
            mock_existing,
            Exception("Update failed"),
        ]

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to update image analysis"):
            await repository.update(sample_image_entity)
        mock_session.rollback.assert_called_once()


@pytest.mark.unit
class TestImageRepositoryDelete:
    """Test cases for ImageRepository.delete()."""

    @pytest.mark.asyncio
    async def test_delete_success(self, mock_session: AsyncMock) -> None:
        """Test successful deletion of image analysis record."""
        # Arrange
        repository = ImageRepository(mock_session)

        # Mock get_by_id call
        mock_existing = Mock()
        mock_existing.first.return_value = Mock(id=1, filename="test.jpg")
        mock_session.execute.return_value = mock_existing

        # Act
        await repository.delete(1)

        # Assert
        assert mock_session.execute.call_count == 2  # get_by_id + delete
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_session: AsyncMock) -> None:
        """Test delete fails when entity doesn't exist."""
        # Arrange
        repository = ImageRepository(mock_session)
        mock_result = Mock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ResourceNotFoundError):
            await repository.delete(999)

    @pytest.mark.asyncio
    async def test_delete_database_error(self, mock_session: AsyncMock) -> None:
        """Test delete handles database errors properly."""
        # Arrange
        repository = ImageRepository(mock_session)

        # Mock get_by_id success, delete fails
        mock_existing = Mock()
        mock_existing.first.return_value = Mock(id=1)
        mock_session.execute.side_effect = [
            mock_existing,
            Exception("Delete failed"),
        ]

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to delete image analysis"):
            await repository.delete(1)
        mock_session.rollback.assert_called_once()


@pytest.mark.unit
class TestImageRepositoryCount:
    """Test cases for ImageRepository.count()."""

    @pytest.mark.asyncio
    async def test_count_success(self, mock_session: AsyncMock) -> None:
        """Test successful count of image analyses."""
        # Arrange
        repository = ImageRepository(mock_session)
        mock_result = Mock()
        mock_result.scalar_one.return_value = 5
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.count()

        # Assert
        assert result == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_zero(self, mock_session: AsyncMock) -> None:
        """Test count returns zero when no records exist."""
        # Arrange
        repository = ImageRepository(mock_session)
        mock_result = Mock()
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.count()

        # Assert
        assert result == 0

    @pytest.mark.asyncio
    async def test_count_database_error(self, mock_session: AsyncMock) -> None:
        """Test count handles database errors properly."""
        # Arrange
        repository = ImageRepository(mock_session)
        mock_session.execute.side_effect = Exception("Query failed")

        # Act & Assert
        with pytest.raises(DatabaseError, match="Failed to count image analyses"):
            await repository.count()
