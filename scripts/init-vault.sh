#!/bin/bash
# Vault initialization script for development
# This script helps initialize and unseal Vault in dev mode

set -e

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_ROOT_TOKEN:-dev-root-token}"

echo "Initializing Vault at ${VAULT_ADDR}..."

# Check if Vault is running
if ! curl -s "${VAULT_ADDR}/v1/sys/health" > /dev/null 2>&1; then
    echo "Error: Vault is not accessible at ${VAULT_ADDR}"
    echo "Make sure Vault container is running: docker-compose up -d vault"
    exit 1
fi

# In dev mode, Vault is already unsealed
# This script is mainly for documentation and future production setup
echo "Vault is running in dev mode and is already unsealed."
echo "Root token: ${VAULT_TOKEN}"
echo ""
echo "To use Vault CLI:"
echo "  export VAULT_ADDR=${VAULT_ADDR}"
echo "  export VAULT_TOKEN=${VAULT_TOKEN}"
echo "  vault status"
echo ""
echo "To access via web UI:"
echo "  http://localhost/vault/"

