#!/bin/bash
# Initialize PostgreSQL databases for Odin services
# This script creates necessary databases if they don't exist

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Initializing PostgreSQL databases...${NC}"

# Check if PostgreSQL container is running
if ! docker ps | grep -q odin-postgresql; then
    echo -e "${RED}Error: PostgreSQL container is not running${NC}"
    echo "Start it with: docker-compose up -d postgresql"
    exit 1
fi

# Wait for PostgreSQL to be ready
echo -e "${BLUE}Waiting for PostgreSQL to be ready...${NC}"
for i in {1..30}; do
    if docker exec odin-postgresql pg_isready -U odin > /dev/null 2>&1; then
        echo -e "${GREEN}PostgreSQL is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Error: PostgreSQL did not become ready in time${NC}"
        exit 1
    fi
    sleep 1
done

# Create odin_db if it doesn't exist
echo -e "${BLUE}Checking odin_db database...${NC}"
if docker exec odin-postgresql psql -U odin -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='odin_db'" | grep -q 1; then
    echo -e "${YELLOW}Database 'odin_db' already exists${NC}"
else
    echo -e "${BLUE}Creating 'odin_db' database...${NC}"
    docker exec odin-postgresql psql -U odin -d postgres -c "CREATE DATABASE odin_db;"
    echo -e "${GREEN}✓ Database 'odin_db' created${NC}"
fi

# Create n8n database if it doesn't exist
echo -e "${BLUE}Checking n8n database...${NC}"
if docker exec odin-postgresql psql -U odin -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='n8n'" | grep -q 1; then
    echo -e "${YELLOW}Database 'n8n' already exists${NC}"
else
    echo -e "${BLUE}Creating 'n8n' database...${NC}"
    docker exec odin-postgresql psql -U odin -d postgres -c "CREATE DATABASE n8n;"
    echo -e "${GREEN}✓ Database 'n8n' created${NC}"
fi

# Initialize logging schema in odin_db
echo -e "${BLUE}Initializing logging schema...${NC}"
if [ -f "scripts/init-logging.sql" ]; then
    docker exec -i odin-postgresql psql -U odin -d odin_db < scripts/init-logging.sql
    echo -e "${GREEN}✓ Logging schema initialized${NC}"
else
    echo -e "${YELLOW}Warning: scripts/init-logging.sql not found, skipping logging schema initialization${NC}"
fi

echo -e "${GREEN}✓ PostgreSQL initialization complete!${NC}"
echo -e "${BLUE}Available databases:${NC}"
docker exec odin-postgresql psql -U odin -d postgres -c "\l" | grep -E "odin_db|n8n|Name" || true

