"""Unit tests for Vault secret management service.

This module tests the Vault service client for secret operations
and authentication.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.api.services.vault import VaultService


class TestVaultService:
    """Test suite for VaultService."""

    @pytest.fixture
    def vault_service(self) -> VaultService:
        """Create a VaultService instance."""
        return VaultService(addr="http://vault:8200", token="dev-token")

    def test_vault_service_initialization(self) -> None:
        """Test that VaultService initializes with address and token."""
        service = VaultService(addr="http://vault:8200", token="test-token")
        assert service.addr == "http://vault:8200"
        assert service.token == "test-token"

    def test_get_client_creates_client(self, vault_service: VaultService) -> None:
        """Test that get_client creates a Vault client."""
        with patch("src.api.services.vault.hvac.Client") as mock_client:
            mock_hvac = MagicMock()
            mock_client.return_value = mock_hvac
            
            client = vault_service.get_client()
            
            assert client == mock_hvac
            mock_client.assert_called_once_with(
                url="http://vault:8200", token="dev-token"
            )

    def test_write_secret_success(self, vault_service: VaultService) -> None:
        """Test write_secret stores a secret in Vault."""
        with patch.object(vault_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            vault_service.write_secret("secret/data/myapp", {"password": "secret123"})
            
            mock_client.secrets.kv.v2.create_or_update_secret.assert_called_once_with(
                path="secret/data/myapp", secret={"password": "secret123"}
            )

    def test_read_secret_success(self, vault_service: VaultService) -> None:
        """Test read_secret retrieves a secret from Vault."""
        with patch.object(vault_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = {"data": {"data": {"password": "secret123"}}}
            mock_client.secrets.kv.v2.read_secret_version.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            result = vault_service.read_secret("secret/data/myapp")
            
            assert result == {"password": "secret123"}
            mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
                path="secret/data/myapp"
            )

    def test_read_secret_returns_none_when_not_found(self, vault_service: VaultService) -> None:
        """Test read_secret returns None when secret does not exist."""
        with patch.object(vault_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception("Not found")
            mock_get_client.return_value = mock_client
            
            result = vault_service.read_secret("secret/data/nonexistent")
            
            assert result is None

    def test_delete_secret_success(self, vault_service: VaultService) -> None:
        """Test delete_secret removes a secret from Vault."""
        with patch.object(vault_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            vault_service.delete_secret("secret/data/myapp")
            
            mock_client.secrets.kv.v2.delete_metadata_and_all_versions.assert_called_once_with(
                path="secret/data/myapp"
            )

    def test_list_secrets_success(self, vault_service: VaultService) -> None:
        """Test list_secrets returns list of secrets at path."""
        with patch.object(vault_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = {"data": {"keys": ["secret1", "secret2"]}}
            mock_client.secrets.kv.v2.list_secrets.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            result = vault_service.list_secrets("secret/data")
            
            assert result == ["secret1", "secret2"]
            mock_client.secrets.kv.v2.list_secrets.assert_called_once_with(path="secret/data")

    def test_list_secrets_returns_empty_when_path_not_found(
        self, vault_service: VaultService
    ) -> None:
        """Test list_secrets returns empty list when path does not exist."""
        with patch.object(vault_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.secrets.kv.v2.list_secrets.side_effect = Exception("Not found")
            mock_get_client.return_value = mock_client
            
            result = vault_service.list_secrets("secret/data/nonexistent")
            
            assert result == []

    def test_health_check_success(self, vault_service: VaultService) -> None:
        """Test health check returns True when Vault is accessible."""
        with patch.object(vault_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.is_authenticated.return_value = True
            mock_get_client.return_value = mock_client
            
            result = vault_service.health_check()
            
            assert result is True
            mock_client.is_authenticated.assert_called_once()

    def test_health_check_failure(self, vault_service: VaultService) -> None:
        """Test health check returns False when Vault is not accessible."""
        with patch.object(vault_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.is_authenticated.side_effect = Exception("Connection failed")
            mock_get_client.return_value = mock_client
            
            result = vault_service.health_check()
            
            assert result is False

