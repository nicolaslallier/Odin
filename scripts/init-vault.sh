#!/bin/bash
# Vault initialization script for development
# This script helps initialize and unseal Vault in dev mode

set -e

VAULT_CONTAINER="odin-vault"
VAULT_TOKEN="${VAULT_ROOT_TOKEN:-dev-root-token}"

echo "Initializing Vault..."

# Check if Vault container is running
if ! docker ps | grep -q "${VAULT_CONTAINER}"; then
    echo "Error: Vault container is not running"
    echo "Make sure Vault container is running: docker-compose up -d vault"
    exit 1
fi

# Check Vault status using docker exec
if ! docker exec "${VAULT_CONTAINER}" vault status > /dev/null 2>&1; then
    echo "Warning: Vault status check failed, but continuing..."
fi

# In dev mode, Vault is already unsealed
echo "✓ Vault is running in dev mode and is already unsealed."
echo "  Root token: ${VAULT_TOKEN}"
echo ""
echo "To use Vault CLI from host:"
echo "  docker exec -it ${VAULT_CONTAINER} sh -c 'export VAULT_ADDR=http://127.0.0.1:8200 && export VAULT_TOKEN=${VAULT_TOKEN} && vault status'"
echo ""
echo "To access via web UI:"
echo "  http://localhost/vault/"
echo ""
echo "=== Setting up Confluence credentials ==="
echo "To configure Confluence integration, store your credentials in Vault:"
echo ""
echo "docker exec -i ${VAULT_CONTAINER} sh -c 'export VAULT_ADDR=http://127.0.0.1:8200 && \\"
echo "export VAULT_TOKEN=${VAULT_TOKEN} && \\"
echo "vault kv put secret/confluence/credentials \\"
echo "  base_url=\"https://your-domain.atlassian.net/wiki\" \\"
echo "  email=\"your-email@domain.com\" \\"
echo "  api_token=\"your-api-token\"'"
echo ""
echo "Get your Confluence API token from:"
echo "https://id.atlassian.com/manage-profile/security/api-tokens"
echo ""
echo "✓ Vault initialization complete!"
echo ""

