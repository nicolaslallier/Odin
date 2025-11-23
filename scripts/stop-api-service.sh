#!/bin/bash
# Stop a specific API microservice

set -e

# Configuration
COMPOSE_FILE="${DOCKER_COMPOSE_FILE:-docker-compose.yml}"
PROJECT_NAME="${DOCKER_COMPOSE_PROJECT:-odin}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Service name mapping
declare -A SERVICE_MAP=(
    ["confluence"]="api-confluence"
    ["files"]="api-files"
    ["llm"]="api-llm"
    ["health"]="api-health"
    ["logs"]="api-logs"
    ["data"]="api-data"
    ["secrets"]="api-secrets"
    ["messages"]="api-messages"
    ["image-analysis"]="api-image-analysis"
)

# Check if service name provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Service name required${NC}"
    echo "Usage: $0 <service-name>"
    echo ""
    echo "Available services:"
    for key in "${!SERVICE_MAP[@]}"; do
        echo "  - $key"
    done
    exit 1
fi

SERVICE_NAME="$1"
COMPOSE_SERVICE="${SERVICE_MAP[$SERVICE_NAME]}"

if [ -z "$COMPOSE_SERVICE" ]; then
    echo -e "${RED}Error: Unknown service '$SERVICE_NAME'${NC}"
    echo "Available services: ${!SERVICE_MAP[@]}"
    exit 1
fi

echo -e "${YELLOW}Stopping API microservice: $SERVICE_NAME${NC}"

# Stop the service with docker-compose
if docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" stop "$COMPOSE_SERVICE"; then
    echo -e "${GREEN}✓ Service $SERVICE_NAME stopped successfully${NC}"
    exit 0
else
    echo -e "${RED}✗ Failed to stop service $SERVICE_NAME${NC}"
    exit 1
fi

