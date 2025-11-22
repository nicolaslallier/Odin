"""HashiCorp Vault service client.

This module provides secret management operations using HashiCorp Vault
for the API service.
"""

from __future__ import annotations

from typing import Any, Optional

import hvac


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
        self._client: Optional[hvac.Client] = None

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
        """
        client = self.get_client()
        client.secrets.kv.v2.create_or_update_secret(path=path, secret=secret)

    def read_secret(self, path: str) -> Optional[dict[str, Any]]:
        """Read a secret from Vault.

        Args:
            path: Path where secret is stored

        Returns:
            Dictionary containing secret data, or None if not found
        """
        try:
            client = self.get_client()
            response = client.secrets.kv.v2.read_secret_version(path=path)
            return response["data"]["data"]
        except Exception:
            return None

    def delete_secret(self, path: str) -> None:
        """Delete a secret from Vault.

        Args:
            path: Path of secret to delete
        """
        client = self.get_client()
        client.secrets.kv.v2.delete_metadata_and_all_versions(path=path)

    def list_secrets(self, path: str) -> list[str]:
        """List secrets at a given path.

        Args:
            path: Path to list secrets from

        Returns:
            List of secret names at the path
        """
        try:
            client = self.get_client()
            response = client.secrets.kv.v2.list_secrets(path=path)
            return response["data"]["keys"]
        except Exception:
            return []

    def health_check(self) -> bool:
        """Check if Vault connection is healthy.

        Returns:
            True if Vault is accessible and authenticated, False otherwise
        """
        try:
            client = self.get_client()
            return client.is_authenticated()
        except Exception:
            return False

