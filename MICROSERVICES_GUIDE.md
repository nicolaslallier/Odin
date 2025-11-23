# Odin Microservices Architecture Guide

## Overview

The Odin API has been split into 9 independent microservices, each handling a specific domain of functionality. This architecture enables:

- **Resource Efficiency**: Services can be independently started, stopped, and scaled
- **Automatic Shutdown**: Inactive services automatically shut down after 5 minutes (configurable)
- **Isolation**: Failures in one service don't affect others
- **Independent Scaling**: Scale services based on individual load patterns
- **Development Flexibility**: Run only the services you need during development

## Architecture

### Microservices

Each microservice is a FastAPI application handling a specific domain:

| Service | Port | Container Name | Description |
|---------|------|----------------|-------------|
| **confluence** | 8001 | odin-api-confluence | Confluence operations and statistics |
| **files** | 8002 | odin-api-files | File storage and management (MinIO) |
| **llm** | 8003 | odin-api-llm | LLM/Ollama operations |
| **health** | 8004 | odin-api-health | Health checks and monitoring |
| **logs** | 8005 | odin-api-logs | Log management and querying |
| **data** | 8006 | odin-api-data | Generic CRUD data operations |
| **secrets** | 8007 | odin-api-secrets | Vault secrets management |
| **messages** | 8008 | odin-api-messages | RabbitMQ messaging |
| **image-analysis** | 8009 | odin-api-image-analysis | Image analysis with vision models |

### Routing

Nginx acts as a reverse proxy and routes requests to appropriate microservices:

```
Browser Request              Nginx Routing              Microservice
---------------              -------------              ------------
/api/confluence/...    -->   /confluence/...      -->   api-confluence:8001
/api/files/...         -->   /files/...           -->   api-files:8002
/api/llm/...           -->   /llm/...             -->   api-llm:8003
/api/health/...        -->   /health/...          -->   api-health:8004
/api/logs/...          -->   /logs/...            -->   api-logs:8005
/api/data/...          -->   /data/...            -->   api-data:8006
/api/secrets/...       -->   /secrets/...         -->   api-secrets:8007
/api/messages/...      -->   /messages/...        -->   api-messages:8008
/api/image-analysis/...-->   /image-analysis/...  -->   api-image-analysis:8009
```

### Shared Infrastructure

All microservices share the same infrastructure services:

- **PostgreSQL**: Database for persistent storage
- **MinIO**: Object storage for files and images
- **RabbitMQ**: Message queue for async tasks
- **Vault**: Secrets management
- **Ollama**: LLM backend

This design ensures **no data duplication** and **consistent state** across services.

## Starting and Stopping Services

### Start All Services

```bash
docker-compose --profile all up -d
```

### Start Specific Services

Start a single service:

```bash
./scripts/start-api-service.sh confluence
```

Start multiple services:

```bash
./scripts/start-api-service.sh confluence
./scripts/start-api-service.sh files
./scripts/start-api-service.sh llm
```

Or with docker-compose profiles:

```bash
docker-compose --profile confluence --profile files up -d
```

### Stop Specific Services

```bash
./scripts/stop-api-service.sh confluence
```

### List Service Status

```bash
./scripts/list-api-services.sh
```

Output example:
```
=== Odin API Microservices Status ===

SERVICE              PORT       STATUS          IDLE TIME
-------              ----       ------          ---------
api-confluence       8001       RUNNING         45s
api-files            8002       STOPPED         -
api-llm              8003       RUNNING         120s
...
```

## Inactivity Auto-Shutdown

### How It Works

Each microservice tracks its activity using middleware:

1. **Activity Tracking**: Every request (except `/internal/*` endpoints) updates the last activity timestamp
2. **Activity Monitoring**: The `check-service-inactivity.py` script polls each service's `/internal/activity` endpoint
3. **Auto Shutdown**: If a service is idle for longer than `INACTIVITY_TIMEOUT_SECONDS`, it's gracefully stopped
4. **On-Demand Restart**: When a request arrives for a stopped service, it must be manually restarted (or configured with orchestration)

### Configuration

Set the inactivity timeout (default: 300 seconds = 5 minutes):

```bash
export INACTIVITY_TIMEOUT_SECONDS=600  # 10 minutes
```

### Running the Monitor

Manual check:

```bash
python scripts/check-service-inactivity.py
```

As a cron job (check every minute):

```bash
*/1 * * * * cd /path/to/odin && python scripts/check-service-inactivity.py >> /var/log/odin-inactivity.log 2>&1
```

As a systemd timer or Docker container (for production).

### Activity Metrics Endpoint

Each service exposes internal activity metrics:

```bash
curl http://localhost:8001/internal/activity
```

Response:
```json
{
  "idle_seconds": 45.2,
  "uptime_seconds": 3600.5,
  "request_count": 127,
  "last_activity_timestamp": 1234567890.123
}
```

## Development Workflow

### Minimal Setup

Start only core infrastructure and the services you need:

```bash
# Start infrastructure
docker-compose up -d postgresql rabbitmq vault minio ollama

# Start only needed API services
./scripts/start-api-service.sh data
./scripts/start-api-service.sh files
```

### Full Development

All services for integration testing:

```bash
docker-compose --profile all up -d
```

### Production-Like Testing

Test auto-shutdown behavior:

```bash
# Start services
./scripts/start-api-service.sh confluence

# Wait 5+ minutes without requests

# Run inactivity check
python scripts/check-service-inactivity.py

# Service should be stopped
./scripts/list-api-services.sh
```

## Service Implementation

### Creating a Microservice

Each microservice uses a common pattern:

**1. App Factory** (`src/api/apps/<service>_app.py`):

```python
from fastapi import FastAPI
from src.api.apps.base import create_base_app
from src.api.routes.<service> import router

def create_app(config: APIConfig | None = None) -> FastAPI:
    app = create_base_app("<service>", config=config)
    app.include_router(router)
    return app
```

**2. Entry Point** (`src/api/apps/__main__<service>__.py`):

```python
import uvicorn
from src.api.apps.<service>_app import create_app
from src.api.config import get_config

if __name__ == "__main__":
    config = get_config()
    app = create_app(config)
    uvicorn.run(app, host=config.host, port=config.port, ...)
```

**3. Docker Compose Service**:

```yaml
api-<service>:
  container_name: odin-api-<service>
  command: python -m src.api.apps.__main__<service>__
  environment:
    - API_PORT=800X
    - INACTIVITY_TIMEOUT_SECONDS=300
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:800X/internal/activity"]
  restart: "no"
  profiles:
    - all
    - <service>
```

### Shared Components

All services use:

- **Base App Factory** (`src/api/apps/base.py`): Common lifespan, error handlers, inactivity tracking
- **Service Container** (`src/api/services/container.py`): Dependency injection for shared services
- **Inactivity Middleware** (`src/api/middleware/inactivity_tracker.py`): Activity tracking

## Nginx Configuration

Routing configuration in `nginx/nginx.conf`:

```nginx
upstream api_confluence {
    server api-confluence:8001;
}

location /api/confluence/ {
    rewrite ^/api/confluence/(.*) /confluence/$1 break;
    proxy_pass http://api_confluence;
    proxy_intercept_errors on;
    error_page 502 503 504 = @api_unavailable;
}

location @api_unavailable {
    return 503 '{"detail": "API service temporarily unavailable..."}';
}
```

## Testing

### Unit Tests

Test individual microservice apps:

```bash
pytest tests/unit/api/apps/
```

### Integration Tests

Test microservice routing and interactions:

```bash
pytest tests/integration/api/
```

### Manual Testing

Test a specific microservice:

```bash
# Start service
./scripts/start-api-service.sh confluence

# Test endpoint
curl http://localhost:8001/internal/activity

# Test through nginx
curl http://localhost/api/confluence/...
```

## Troubleshooting

### Service Won't Start

1. Check dependencies are running:
   ```bash
   docker-compose ps
   ```

2. Check logs:
   ```bash
   docker-compose logs api-confluence
   ```

3. Check for port conflicts:
   ```bash
   netstat -tulpn | grep 8001
   ```

### Service Immediately Stops

Check restart policy is `"no"` (intended behavior) or `"unless-stopped"` (auto-restart):

```yaml
restart: "no"  # Manual start only
```

### Nginx 503 Errors

Service is down or starting:

1. Check service status:
   ```bash
   ./scripts/list-api-services.sh
   ```

2. Start the service:
   ```bash
   ./scripts/start-api-service.sh <service>
   ```

3. Wait for health check to pass

### Inactivity Monitor Not Working

1. Check script can reach services:
   ```bash
   curl http://localhost:8001/internal/activity
   ```

2. Check environment variables:
   ```bash
   echo $INACTIVITY_TIMEOUT_SECONDS
   ```

3. Run with debug logging:
   ```bash
   python scripts/check-service-inactivity.py
   ```

## Production Considerations

### Container Orchestration

For production, consider:

- **Kubernetes**: Use HPA (Horizontal Pod Autoscaler) for auto-scaling
- **Docker Swarm**: Use replicas and health checks
- **Service Mesh**: Istio or Linkerd for advanced routing

### Monitoring

Add monitoring for:

- Service uptime and availability
- Request rates per service
- Resource usage per service
- Idle time trends

### Logging

All services use structured JSON logging to PostgreSQL. Monitor:

- Error rates per service
- Request latency per service
- Activity patterns

### Security

- Services communicate within Docker network (not exposed externally)
- Nginx is the only public-facing component
- All services share authentication/authorization via Vault

## Migration from Monolithic API

### Before (Monolithic)

```
/api/confluence/...  -->  odin-api:8001 (all endpoints)
/api/files/...       -->  odin-api:8001 (all endpoints)
/api/llm/...         -->  odin-api:8001 (all endpoints)
```

### After (Microservices)

```
/api/confluence/...  -->  api-confluence:8001 (specialized)
/api/files/...       -->  api-files:8002 (specialized)
/api/llm/...         -->  api-llm:8003 (specialized)
```

### Compatibility

**No breaking changes** for clients:

- Same URL patterns through nginx
- Same request/response formats
- Same authentication flow
- Portal requires no changes

## Benefits Summary

✅ **Resource Efficiency**: Only active services consume resources
✅ **Fault Isolation**: Service failures don't cascade
✅ **Independent Scaling**: Scale busy services independently
✅ **Development Speed**: Work on services in isolation
✅ **Deployment Flexibility**: Deploy/update services independently
✅ **Clear Boundaries**: Enforced separation of concerns

## See Also

- [API_GUIDE.md](API_GUIDE.md) - API usage documentation
- [docker-compose.yml](docker-compose.yml) - Service definitions
- [nginx/nginx.conf](nginx/nginx.conf) - Routing configuration
- [scripts/](scripts/) - Management scripts

