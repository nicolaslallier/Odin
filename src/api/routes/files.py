"""File management routes for API service.

This module provides endpoints for file upload, download, and management via MinIO.
"""

from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from src.api.exceptions import ResourceNotFoundError, StorageError
from src.api.models.schemas import FileListResponse, FileUploadResponse
from src.api.services.container import ServiceContainer
from src.api.services.storage import StorageService

router = APIRouter(prefix="/files", tags=["files"])


def get_container(request: Request) -> ServiceContainer:
    """Dependency to get service container from app state.

    Args:
        request: FastAPI request object

    Returns:
        Service container instance
    """
    return request.app.state.container


def get_storage_service(container: ServiceContainer = Depends(get_container)) -> StorageService:
    """Dependency to get storage service instance.

    Args:
        container: Service container

    Returns:
        Storage service instance
    """
    return container.storage


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

    Raises:
        HTTPException: If upload fails
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
    except StorageError as e:
        raise HTTPException(status_code=500, detail=e.message)
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

    Raises:
        HTTPException: If file not found or download fails
    """
    try:
        content = storage.download_file(bucket, key)
        return StreamingResponse(
            BytesIO(content),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={key}"},
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except StorageError as e:
        raise HTTPException(status_code=500, detail=e.message)


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

    Raises:
        HTTPException: If deletion fails
    """
    try:
        storage.delete_file(bucket, key)
        return {"message": f"File {key} deleted successfully"}
    except StorageError as e:
        raise HTTPException(status_code=500, detail=e.message)


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

    Raises:
        HTTPException: If listing fails
    """
    try:
        files = storage.list_files(bucket, prefix)
        return FileListResponse(bucket=bucket, files=files)
    except StorageError as e:
        raise HTTPException(status_code=500, detail=e.message)
