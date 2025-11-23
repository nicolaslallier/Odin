#!/bin/bash
# List all API microservices and their status

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service definitions
SERVICES=(
    "api-confluence:8001:odin-api-confluence"
    "api-files:8002:odin-api-files"
    "api-llm:8003:odin-api-llm"
    "api-health:8004:odin-api-health"
    "api-logs:8005:odin-api-logs"
    "api-data:8006:odin-api-data"
    "api-secrets:8007:odin-api-secrets"
    "api-messages:8008:odin-api-messages"
    "api-image-analysis:8009:odin-api-image-analysis"
)

echo -e "${BLUE}=== Odin API Microservices Status ===${NC}"
echo ""
printf "%-20s %-10s %-15s %-15s\n" "SERVICE" "PORT" "STATUS" "IDLE TIME"
printf "%-20s %-10s %-15s %-15s\n" "-------" "----" "------" "---------"

for service_info in "${SERVICES[@]}"; do
    IFS=':' read -r service port container <<< "$service_info"
    
    # Check if container is running
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        status="${GREEN}RUNNING${NC}"
        
        # Try to get idle time from activity endpoint
        idle_time=$(curl -s "http://localhost:${port}/internal/activity" 2>/dev/null | \
                    python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{int(data.get('idle_seconds', 0))}s\")" 2>/dev/null || echo "N/A")
    else
        status="${RED}STOPPED${NC}"
        idle_time="-"
    fi
    
    printf "%-20s %-10s %-15b %-15s\n" "$service" "$port" "$status" "$idle_time"
done

echo ""
echo -e "${YELLOW}Tip:${NC} Use scripts/start-api-service.sh <name> to start a service"
echo -e "${YELLOW}Tip:${NC} Use scripts/stop-api-service.sh <name> to stop a service"
echo ""

