"""Image analysis service orchestration.

This module provides the orchestration layer for image analysis operations,
coordinating storage, database persistence, and LLM analysis.
"""

from __future__ import annotations

import time
from io import BytesIO
from typing import List, Optional

from src.api.domain.entities import ImageAnalysis
from src.api.exceptions import StorageError, ValidationError
from src.api.repositories.image_repository import ImageRepository
from src.api.services.database import DatabaseService
from src.api.services.ollama import OllamaService
from src.api.services.storage import StorageService


class ImageAnalysisService:
    """Service for orchestrating image analysis operations.

    This service coordinates image storage in MinIO, metadata persistence in PostgreSQL,
    and LLM-powered image analysis via Ollama.

    Attributes:
        storage: Storage service for MinIO operations
        database: Database service for PostgreSQL operations
        ollama: Ollama service for LLM operations
        default_model: Default vision model to use
        image_bucket: MinIO bucket for image storage
        max_size_mb: Maximum allowed image size in megabytes
    """

    SUPPORTED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"]

    def __init__(
        self,
        storage: StorageService,
        database: DatabaseService,
        ollama: OllamaService,
        default_model: str = "llava:latest",
        image_bucket: str = "images",
        max_size_mb: int = 10,
    ) -> None:
        """Initialize image analysis service.

        Args:
            storage: Storage service instance
            database: Database service instance
            ollama: Ollama service instance
            default_model: Default vision model name
            image_bucket: Bucket name for image storage
            max_size_mb: Maximum image size in megabytes
        """
        self.storage = storage
        self.database = database
        self.ollama = ollama
        self.default_model = default_model
        self.image_bucket = image_bucket
        self.max_size_mb = max_size_mb

    def _validate_image(self, file_data: bytes, content_type: str) -> None:
        """Validate image data and content type.

        Args:
            file_data: Image file data
            content_type: MIME content type

        Raises:
            ValidationError: If validation fails
        """
        # Check file size
        size_mb = len(file_data) / (1024 * 1024)
        if size_mb > self.max_size_mb:
            raise ValidationError(
                f"Image size {size_mb:.2f}MB exceeds maximum size {self.max_size_mb}MB"
            )

        # Check content type
        if content_type not in self.SUPPORTED_CONTENT_TYPES:
            raise ValidationError(
                f"Invalid image content type: {content_type}. "
                f"Supported types: {', '.join(self.SUPPORTED_CONTENT_TYPES)}"
            )

    def _generate_object_key(self, filename: str) -> str:
        """Generate unique object key for storage.

        Args:
            filename: Original filename

        Returns:
            Unique object key with timestamp
        """
        # Extract extension
        parts = filename.rsplit(".", 1)
        if len(parts) == 2:
            name, ext = parts
            # Generate unique key with timestamp
            timestamp = int(time.time() * 1000000)  # microseconds for uniqueness
            return f"{name}_{timestamp}.{ext}"
        else:
            # No extension, just append timestamp
            timestamp = int(time.time() * 1000000)
            return f"{filename}_{timestamp}"

    async def analyze_and_store(
        self,
        filename: str,
        file_data: bytes,
        content_type: str,
        prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> ImageAnalysis:
        """Analyze an image and store it with metadata.

        This method orchestrates the full workflow:
        1. Validate image
        2. Upload to MinIO
        3. Analyze with LLM
        4. Store metadata in PostgreSQL

        If any step fails after storage, the uploaded image is cleaned up.

        Args:
            filename: Original filename
            file_data: Image file data as bytes
            content_type: MIME content type
            prompt: Optional custom prompt (default: "Describe this image")
            model: Optional model name (default: configured default_model)

        Returns:
            Created ImageAnalysis entity with ID and analysis

        Raises:
            ValidationError: If image validation fails
            StorageError: If MinIO upload fails
            LLMError: If image analysis fails
            DatabaseError: If database operation fails
        """
        # Validate image
        self._validate_image(file_data, content_type)

        # Use defaults if not provided
        if prompt is None:
            prompt = "Describe this image"
        if model is None:
            model = self.default_model

        # Generate unique object key
        object_key = self._generate_object_key(filename)

        # Ensure bucket exists
        if not self.storage.bucket_exists(self.image_bucket):
            self.storage.create_bucket(self.image_bucket)

        # Upload to MinIO
        file_io = BytesIO(file_data)
        self.storage.upload_file(
            self.image_bucket, object_key, file_io, len(file_data)
        )

        try:
            # Analyze with LLM
            description = await self.ollama.analyze_image(
                model=model,
                prompt=prompt,
                image_data=file_data,
            )

            # Create entity
            analysis = ImageAnalysis(
                filename=filename,
                bucket=self.image_bucket,
                object_key=object_key,
                content_type=content_type,
                size_bytes=len(file_data),
                llm_description=description,
                model_used=model,
            )

            # Store in database
            async with self.database.get_session() as session:
                repository = ImageRepository(session)
                result = await repository.create(analysis)

            return result

        except Exception as e:
            # Cleanup: delete uploaded image if analysis or DB storage fails
            try:
                self.storage.delete_file(self.image_bucket, object_key)
            except StorageError:
                # Log but don't raise - original error is more important
                pass
            raise

    async def get_analysis(self, image_id: int) -> ImageAnalysis:
        """Get image analysis by ID.

        Args:
            image_id: ID of the image analysis

        Returns:
            ImageAnalysis entity

        Raises:
            ResourceNotFoundError: If analysis not found
            DatabaseError: If database operation fails
        """
        async with self.database.get_session() as session:
            repository = ImageRepository(session)
            return await repository.get_by_id(image_id)

    async def list_analyses(self) -> List[ImageAnalysis]:
        """List all image analyses.

        Returns:
            List of ImageAnalysis entities

        Raises:
            DatabaseError: If database operation fails
        """
        async with self.database.get_session() as session:
            repository = ImageRepository(session)
            return await repository.get_all()

    async def delete_analysis(self, image_id: int) -> None:
        """Delete image analysis and associated image file.

        Args:
            image_id: ID of the image analysis to delete

        Raises:
            ResourceNotFoundError: If analysis not found
            DatabaseError: If database operation fails
        """
        # Get analysis to retrieve storage info
        async with self.database.get_session() as session:
            repository = ImageRepository(session)
            analysis = await repository.get_by_id(image_id)

            # Delete from storage (best effort - continue even if fails)
            try:
                self.storage.delete_file(analysis.bucket, analysis.object_key)
            except StorageError:
                # Continue with DB deletion even if storage deletion fails
                pass

            # Delete from database
            await repository.delete(image_id)

