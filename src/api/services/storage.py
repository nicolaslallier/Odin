"""MinIO storage service client.

This module provides object storage operations using MinIO S3-compatible API
for file management in the API service.
"""

from __future__ import annotations

import asyncio
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from src.api.exceptions import ResourceNotFoundError, ServiceUnavailableError, StorageError


class StorageService:
    """MinIO storage service client.

    This class provides file storage operations using MinIO's S3-compatible API.

    Attributes:
        endpoint: MinIO server endpoint
        access_key: MinIO access key
        secret_key: MinIO secret key
        secure: Whether to use HTTPS
    """

    def __init__(
        self, endpoint: str, access_key: str, secret_key: str, secure: bool = False
    ) -> None:
        """Initialize storage service with MinIO credentials.

        Args:
            endpoint: MinIO server endpoint (e.g., minio:9000)
            access_key: MinIO access key
            secret_key: MinIO secret key
            secure: Whether to use HTTPS for connection
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self._client: Minio | None = None

    def get_client(self) -> Minio:
        """Get or create the MinIO client.

        Returns:
            MinIO client instance
        """
        if self._client is None:
            self._client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
        return self._client

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists.

        Args:
            bucket_name: Name of the bucket to check

        Returns:
            True if bucket exists, False otherwise

        Raises:
            ServiceUnavailableError: If MinIO is unreachable
        """
        try:
            client = self.get_client()
            return client.bucket_exists(bucket_name)
        except S3Error as e:
            raise ServiceUnavailableError(f"MinIO error: {e}")
        except Exception as e:
            raise ServiceUnavailableError(f"Failed to check bucket existence: {e}")

    def create_bucket(self, bucket_name: str) -> None:
        """Create a new bucket.

        Args:
            bucket_name: Name of the bucket to create

        Raises:
            StorageError: If bucket creation fails
        """
        try:
            client = self.get_client()
            if not self.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)
        except S3Error as e:
            raise StorageError(f"Failed to create bucket: {e}", {"bucket": bucket_name})
        except Exception as e:
            raise StorageError(f"Unexpected error creating bucket: {e}", {"bucket": bucket_name})

    def upload_file(self, bucket_name: str, object_name: str, data: BinaryIO, length: int) -> None:
        """Upload a file to bucket.

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object to create
            data: File-like object containing data
            length: Length of data in bytes

        Raises:
            StorageError: If file upload fails
        """
        try:
            client = self.get_client()
            client.put_object(bucket_name, object_name, data, length)
        except S3Error as e:
            raise StorageError(
                f"Failed to upload file: {e}",
                {"bucket": bucket_name, "object": object_name},
            )

    def download_file(self, bucket_name: str, object_name: str) -> bytes:
        """Download a file from bucket.

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object to download

        Returns:
            File contents as bytes

        Raises:
            ResourceNotFoundError: If file not found
            StorageError: If download fails
        """
        try:
            client = self.get_client()
            response = client.get_object(bucket_name, object_name)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise ResourceNotFoundError(
                    f"File not found: {object_name}",
                    {"bucket": bucket_name, "object": object_name},
                )
            raise StorageError(
                f"Failed to download file: {e}",
                {"bucket": bucket_name, "object": object_name},
            )

    def delete_file(self, bucket_name: str, object_name: str) -> None:
        """Delete a file from bucket.

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object to delete

        Raises:
            StorageError: If deletion fails
        """
        try:
            client = self.get_client()
            client.remove_object(bucket_name, object_name)
        except S3Error as e:
            raise StorageError(
                f"Failed to delete file: {e}",
                {"bucket": bucket_name, "object": object_name},
            )

    def list_files(self, bucket_name: str, prefix: str = "") -> list[str]:
        """List files in a bucket.

        Args:
            bucket_name: Name of the bucket
            prefix: Optional prefix to filter objects

        Returns:
            List of object names

        Raises:
            StorageError: If listing fails
        """
        try:
            client = self.get_client()
            objects = client.list_objects(bucket_name, prefix=prefix)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            raise StorageError(f"Failed to list files: {e}", {"bucket": bucket_name})

    async def health_check(self) -> bool:
        """Check if MinIO connection is healthy.

        This method runs synchronous MinIO operations in a thread pool
        to avoid blocking the event loop.

        Returns:
            True if MinIO is accessible, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            client = self.get_client()
            # Run synchronous list_buckets in thread pool
            await loop.run_in_executor(None, client.list_buckets)
            return True
        except Exception:
            return False
