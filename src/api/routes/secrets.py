"""Secret management routes for API service.

This module provides endpoints for Vault secret operations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.config import APIConfig, get_config
from src.api.models.schemas import SecretRequest, SecretResponse
from src.api.services.vault import VaultService

router = APIRouter(prefix="/secrets", tags=["secrets"])


def get_vault_service(config: APIConfig = Depends(get_config)) -> VaultService:
    """Dependency to get Vault service instance.

    Args:
        config: API configuration

    Returns:
        Vault service instance
    """
    return VaultService(addr=config.vault_addr, token=config.vault_token)


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
    """
    try:
        vault.write_secret(request.path, request.data)
        return {"message": f"Secret written to {request.path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    """
    try:
        data = vault.read_secret(path)
        if data is None:
            raise HTTPException(status_code=404, detail="Secret not found")
        return SecretResponse(path=path, data=data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    """
    try:
        vault.delete_secret(path)
        return {"message": f"Secret at {path} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

