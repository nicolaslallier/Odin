"""HashiCorp Vault service client.

This module provides secret management operations using HashiCorp Vault
for the API service.
"""

from __future__ import annotations

import asyncio
from typing import Any, cast

import hvac

from src.api.exceptions import ResourceNotFoundError, ServiceUnavailableError, VaultError


class VaultService:
    """HashiCorp Vault service client.

    This class provides secret management operations using Vault's KV v2 engine.

    Attributes:
        addr: Vault server address
        token: Vault authentication token
    """

    def __init__(self, addr: str, token: str) -> None:
        """Initialize Vault service with server address and token.

        Args:
            addr: Vault server address (e.g., http://vault:8200)
            token: Vault authentication token
        """
        self.addr = addr
        self.token = token
        self._client: hvac.Client | None = None

    def get_client(self) -> hvac.Client:
        """Get or create the Vault client.

        Returns:
            Vault client instance
        """
        if self._client is None:
            self._client = hvac.Client(url=self.addr, token=self.token)
        return self._client

    def write_secret(self, path: str, secret: dict[str, Any]) -> None:
        """Write a secret to Vault.

        Args:
            path: Path where secret should be stored (e.g., secret/data/myapp)
            secret: Dictionary containing secret key-value pairs

        Raises:
            VaultError: If secret write fails
            ServiceUnavailableError: If Vault is unreachable
        """
        try:
            client = self.get_client()
            client.secrets.kv.v2.create_or_update_secret(path=path, secret=secret)
        except hvac.exceptions.Forbidden as e:
            raise VaultError(f"Permission denied writing secret: {e}", {"path": path})
        except hvac.exceptions.VaultError as e:
            raise VaultError(f"Failed to write secret: {e}", {"path": path})
        except Exception as e:
            raise ServiceUnavailableError(f"Vault unreachable: {e}")

    def read_secret(self, path: str) -> dict[str, Any] | None:
        """Read a secret from Vault.

        Args:
            path: Path where secret is stored

        Returns:
            Dictionary containing secret data, or None if not found

        Raises:
            VaultError: If secret read fails
            ResourceNotFoundError: If secret not found
        """
        try:
            client = self.get_client()
            response = client.secrets.kv.v2.read_secret_version(path=path)
            return cast(dict[str, Any] | None, response["data"]["data"])
        except hvac.exceptions.InvalidPath:
            raise ResourceNotFoundError(f"Secret not found at path: {path}", {"path": path})
        except hvac.exceptions.Forbidden as e:
            raise VaultError(f"Permission denied reading secret: {e}", {"path": path})
        except hvac.exceptions.VaultError as e:
            raise VaultError(f"Failed to read secret: {e}", {"path": path})
        except Exception as e:
            raise ServiceUnavailableError(f"Vault unreachable: {e}")

    def delete_secret(self, path: str) -> None:
        """Delete a secret from Vault.

        Args:
            path: Path of secret to delete

        Raises:
            VaultError: If secret deletion fails
        """
        try:
            client = self.get_client()
            client.secrets.kv.v2.delete_metadata_and_all_versions(path=path)
        except hvac.exceptions.VaultError as e:
            raise VaultError(f"Failed to delete secret: {e}", {"path": path})

    def list_secrets(self, path: str) -> list[str]:
        """List secrets at a given path.

        Args:
            path: Path to list secrets from

        Returns:
            List of secret names at the path

        Raises:
            VaultError: If listing fails
        """
        try:
            client = self.get_client()
            response = client.secrets.kv.v2.list_secrets(path=path)
            return cast(list[str], response["data"]["keys"])
        except hvac.exceptions.InvalidPath:
            return []
        except hvac.exceptions.VaultError as e:
            raise VaultError(f"Failed to list secrets: {e}", {"path": path})

    async def health_check(self) -> bool:
        """Check if Vault connection is healthy.

        This method runs synchronous Vault operations in a thread pool
        to avoid blocking the event loop.

        Returns:
            True if Vault is accessible and authenticated, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            client = self.get_client()
            # Run synchronous is_authenticated in thread pool
            result = await loop.run_in_executor(None, client.is_authenticated)
            return cast(bool, result)
        except Exception:
            return False
