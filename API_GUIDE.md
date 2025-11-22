# Odin API Service Guide

## Overview

The Odin API Service is an internal FastAPI-based REST API that provides comprehensive backend functionality for the Odin project. It connects to PostgreSQL, MinIO, RabbitMQ, Vault, and Ollama to offer data management, file storage, message queuing, secret management, and LLM capabilities.

**Important**: The API is internal-only and not exposed through nginx. It runs on port 8001 and is accessible only within the Docker network at `http://api:8001`.

## Architecture

The API service follows SOLID principles and Test-Driven Development (TDD) with 100% test coverage:

- **Single Responsibility**: Each service handles one backend integration
- **Open/Closed**: Extensible through dependency injection
- **Liskov Substitution**: Consistent service interfaces
- **Interface Segregation**: Focused, specific endpoints
- **Dependency Inversion**: Configuration-driven dependencies

## Service Connections

The API connects to the following services:

| Service    | Endpoint                     | Purpose                      |
|------------|------------------------------|------------------------------|
| PostgreSQL | postgresql:5432              | Relational database          |
| MinIO      | minio:9000                   | S3-compatible object storage |
| RabbitMQ   | rabbitmq:5672                | Message queue                |
| Vault      | vault:8200                   | Secrets management           |
| Ollama     | ollama:11434                 | LLM operations               |

## API Endpoints

### Health Checks

#### `GET /health`
Basic health check for the API service.

**Response:**
```json
{
  "status": "healthy",
  "service": "odin-api"
}
```

#### `GET /health/services`
Check health of all backend services.

**Response:**
```json
{
  "database": true,
  "storage": true,
  "queue": true,
  "vault": true,
  "ollama": true
}
```

### Data Management (CRUD)

#### `POST /data/`
Create a new data item.

**Request Body:**
```json
{
  "name": "Item Name",
  "description": "Item description",
  "data": {}
}
```

#### `GET /data/{id}`
Retrieve a data item by ID.

#### `PUT /data/{id}`
Update a data item.

#### `DELETE /data/{id}`
Delete a data item.

#### `GET /data/`
List all data items.

### File Management

#### `POST /files/upload?bucket={bucket}&key={key}`
Upload a file to MinIO.

**Form Data:**
- `file`: File to upload

#### `GET /files/{key}?bucket={bucket}`
Download a file from MinIO.

#### `DELETE /files/{key}?bucket={bucket}`
Delete a file from MinIO.

#### `GET /files/?bucket={bucket}&prefix={prefix}`
List files in a bucket.

### Message Queue

#### `POST /messages/send`
Send a message to a queue.

**Request Body:**
```json
{
  "queue": "queue-name",
  "message": "Message content"
}
```

#### `GET /messages/receive?queue_name={queue}`
Receive a message from a queue.

### Secret Management

#### `POST /secrets/`
Write a secret to Vault.

**Request Body:**
```json
{
  "path": "secret/data/myapp",
  "data": {
    "password": "secret123",
    "api_key": "key123"
  }
}
```

#### `GET /secrets/{path}`
Read a secret from Vault.

#### `DELETE /secrets/{path}`
Delete a secret from Vault.

### LLM Operations

#### `GET /llm/models`
List available LLM models.

#### `POST /llm/generate`
Generate text using an LLM.

**Request Body:**
```json
{
  "model": "llama2",
  "prompt": "Hello, world!",
  "system": "You are a helpful assistant"
}
```

#### `POST /llm/stream`
Generate text with streaming response.

## Configuration

The API is configured via environment variables:

### API Server Settings
- `API_HOST`: Host address (default: 0.0.0.0)
- `API_PORT`: Port number (default: 8001)
- `API_RELOAD`: Auto-reload in development (default: true)
- `API_LOG_LEVEL`: Logging level (default: info)

### Backend Service Connections
- `POSTGRES_DSN`: PostgreSQL connection string
- `MINIO_ENDPOINT`: MinIO endpoint
- `MINIO_ACCESS_KEY`: MinIO access key
- `MINIO_SECRET_KEY`: MinIO secret key
- `MINIO_SECURE`: Use HTTPS (default: false)
- `RABBITMQ_URL`: RabbitMQ connection URL
- `VAULT_ADDR`: Vault server address
- `VAULT_TOKEN`: Vault authentication token
- `OLLAMA_BASE_URL`: Ollama API base URL

## Development

### Running the API

Start the API service:
```bash
make api-dev
```

View logs:
```bash
make api-logs
```

Access the container:
```bash
make api-shell
```

### Running Tests

Run all API tests:
```bash
make api-test
```

Run tests with coverage:
```bash
make coverage
```

### Accessing from Portal

From within the Docker network (e.g., from the portal service), access the API at:
```
http://api:8001
```

Example Python code:
```python
import httpx

async def call_api():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://api:8001/health")
        return response.json()
```

## API Documentation

Once the API is running, access the auto-generated documentation:

- **Swagger UI**: http://api:8001/docs (internal only)
- **ReDoc**: http://api:8001/redoc (internal only)

Note: These URLs are only accessible from within the Docker network.

## Service Clients

The API includes service client classes for each backend integration:

### DatabaseService
```python
from src.api.services.database import DatabaseService

db = DatabaseService(dsn="postgresql://...")
async with db.get_session() as session:
    result = await session.execute(query)
```

### StorageService
```python
from src.api.services.storage import StorageService

storage = StorageService(endpoint="minio:9000", ...)
storage.upload_file("bucket", "key", file_data, length)
```

### QueueService
```python
from src.api.services.queue import QueueService

queue = QueueService(url="amqp://...")
queue.publish_message("queue-name", "message")
```

### VaultService
```python
from src.api.services.vault import VaultService

vault = VaultService(addr="http://vault:8200", token="...")
vault.write_secret("secret/path", {"key": "value"})
```

### OllamaService
```python
from src.api.services.ollama import OllamaService

ollama = OllamaService(base_url="http://ollama:11434")
response = await ollama.generate_text("llama2", "Hello!")
```

## Testing

The API follows TDD with comprehensive test coverage:

- **Unit Tests**: `tests/unit/api/` - Test individual components
- **Integration Tests**: `tests/integration/api/` - Test full workflows
- **100% Coverage**: All code paths tested

Run specific test categories:
```bash
# Unit tests only
pytest tests/unit/api/ -v

# Integration tests only
pytest tests/integration/api/ -v

# With coverage
pytest --cov=src.api --cov-report=html
```

## Troubleshooting

### API Not Starting
Check logs: `make api-logs`

Verify all backend services are healthy:
```bash
make services-health
```

### Connection Errors
Ensure all dependent services are running:
```bash
docker-compose ps
```

### Health Check Failures
Test individual service connections:
```bash
make api-shell
# Inside container:
curl http://localhost:8001/health/services
```

## Security Notes

**Development Mode**:
- Default credentials are for development only
- Vault runs in dev mode (not production-ready)
- No authentication on API endpoints
- Internal network only (not exposed)

**Production Considerations**:
- Change all default credentials
- Use production-grade Vault configuration
- Add API authentication/authorization
- Enable HTTPS for external connections
- Implement rate limiting
- Add request validation middleware

## Future Enhancements

- Authentication and authorization
- Rate limiting and throttling
- Request/response caching
- WebSocket support for real-time features
- Batch operation endpoints
- Advanced query filtering
- API versioning (v1, v2, etc.)
- GraphQL interface
- Monitoring and metrics endpoints
- Automated API client generation

