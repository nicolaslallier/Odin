"""Secret management routes for API service.

This module provides endpoints for Vault secret operations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.exceptions import ResourceNotFoundError, ServiceUnavailableError, VaultError
from src.api.models.schemas import SecretRequest, SecretResponse
from src.api.services.container import ServiceContainer
from src.api.services.vault import VaultService

router = APIRouter(prefix="/secrets", tags=["secrets"])


def get_container(request: Request) -> ServiceContainer:
    """Dependency to get service container from app state.

    Args:
        request: FastAPI request object

    Returns:
        Service container instance
    """
    return request.app.state.container


def get_vault_service(container: ServiceContainer = Depends(get_container)) -> VaultService:
    """Dependency to get Vault service instance.

    Args:
        container: Service container

    Returns:
        Vault service instance
    """
    return container.vault


@router.post("/")
async def write_secret(
    request: SecretRequest,
    vault: VaultService = Depends(get_vault_service),
) -> dict[str, str]:
    """Write a secret to Vault.

    Args:
        request: Secret request with path and data
        vault: Vault service instance

    Returns:
        Confirmation message

    Raises:
        HTTPException: If write fails
    """
    try:
        vault.write_secret(request.path, request.data)
        return {"message": f"Secret written to {request.path}"}
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=e.message)
    except VaultError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/{path:path}", response_model=SecretResponse)
async def read_secret(
    path: str,
    vault: VaultService = Depends(get_vault_service),
) -> SecretResponse:
    """Read a secret from Vault.

    Args:
        path: Path to the secret
        vault: Vault service instance

    Returns:
        Secret data response

    Raises:
        HTTPException: If read fails or secret not found
    """
    try:
        data = vault.read_secret(path)
        return SecretResponse(path=path, data=data)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=e.message)
    except VaultError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.delete("/{path:path}")
async def delete_secret(
    path: str,
    vault: VaultService = Depends(get_vault_service),
) -> dict[str, str]:
    """Delete a secret from Vault.

    Args:
        path: Path to the secret
        vault: Vault service instance

    Returns:
        Confirmation message

    Raises:
        HTTPException: If deletion fails
    """
    try:
        vault.delete_secret(path)
        return {"message": f"Secret at {path} deleted"}
    except VaultError as e:
        raise HTTPException(status_code=500, detail=e.message)

