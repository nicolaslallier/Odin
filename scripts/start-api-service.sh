#!/bin/bash
# Start a specific API microservice

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

echo -e "${YELLOW}Starting API microservice: $SERVICE_NAME${NC}"

# Start the service with docker-compose
if docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" --profile "$SERVICE_NAME" up -d "$COMPOSE_SERVICE"; then
    echo -e "${GREEN}✓ Service $SERVICE_NAME started successfully${NC}"
    
    # Wait for health check
    echo "Waiting for service to be healthy..."
    for i in {1..30}; do
        if docker inspect --format='{{.State.Health.Status}}' "odin-$COMPOSE_SERVICE" 2>/dev/null | grep -q "healthy"; then
            echo -e "${GREEN}✓ Service is healthy${NC}"
            exit 0
        fi
        echo -n "."
        sleep 2
    done
    
    echo -e "${YELLOW}⚠ Service started but health check timeout${NC}"
    exit 0
else
    echo -e "${RED}✗ Failed to start service $SERVICE_NAME${NC}"
    exit 1
fi

