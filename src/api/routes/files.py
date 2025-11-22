"""File management routes for API service.

This module provides endpoints for file upload, download, and management via MinIO.
"""

from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from src.api.config import APIConfig, get_config
from src.api.models.schemas import FileListResponse, FileUploadResponse
from src.api.services.storage import StorageService

router = APIRouter(prefix="/files", tags=["files"])


def get_storage_service(config: APIConfig = Depends(get_config)) -> StorageService:
    """Dependency to get storage service instance.

    Args:
        config: API configuration

    Returns:
        Storage service instance
    """
    return StorageService(
        endpoint=config.minio_endpoint,
        access_key=config.minio_access_key,
        secret_key=config.minio_secret_key,
        secure=config.minio_secure,
    )


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    bucket: str,
    key: str,
    file: UploadFile = File(...),
    storage: StorageService = Depends(get_storage_service),
) -> FileUploadResponse:
    """Upload a file to MinIO.

    Args:
        bucket: Bucket name
        key: Object key/name
        file: File to upload
        storage: Storage service instance

    Returns:
        Upload confirmation response
    """
    try:
        # Ensure bucket exists
        if not storage.bucket_exists(bucket):
            storage.create_bucket(bucket)

        # Read file content
        content = await file.read()
        file_data = BytesIO(content)

        # Upload to MinIO
        storage.upload_file(bucket, key, file_data, len(content))

        return FileUploadResponse(
            bucket=bucket, key=key, message=f"File {key} uploaded successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{key}")
async def download_file(
    key: str,
    bucket: str,
    storage: StorageService = Depends(get_storage_service),
) -> StreamingResponse:
    """Download a file from MinIO.

    Args:
        key: Object key/name
        bucket: Bucket name
        storage: Storage service instance

    Returns:
        File content as streaming response
    """
    try:
        content = storage.download_file(bucket, key)
        return StreamingResponse(
            BytesIO(content),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={key}"},
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")


@router.delete("/{key}")
async def delete_file(
    key: str,
    bucket: str,
    storage: StorageService = Depends(get_storage_service),
) -> dict[str, str]:
    """Delete a file from MinIO.

    Args:
        key: Object key/name
        bucket: Bucket name
        storage: Storage service instance

    Returns:
        Deletion confirmation message
    """
    try:
        storage.delete_file(bucket, key)
        return {"message": f"File {key} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=FileListResponse)
async def list_files(
    bucket: str,
    prefix: str = "",
    storage: StorageService = Depends(get_storage_service),
) -> FileListResponse:
    """List files in a bucket.

    Args:
        bucket: Bucket name
        prefix: Optional prefix to filter files
        storage: Storage service instance

    Returns:
        List of files in bucket
    """
    try:
        files = storage.list_files(bucket, prefix)
        return FileListResponse(bucket=bucket, files=files)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

