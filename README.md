# Odin

![Version](https://img.shields.io/badge/version-0.4.3-blue.svg)
![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-131%20passed-brightgreen.svg)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)

A Python project following Test-Driven Development (TDD), SOLID principles, and industry best practices with comprehensive testing and Docker containerization.

## Overview

Odin is a Python development environment configured for senior-level development practices, emphasizing:

- **Test-Driven Development (TDD)**: Write tests first, then implement
- **SOLID Principles**: Clean, maintainable, and extensible code architecture
- **High Test Coverage**: 100% coverage for web portal (54 tests) and complete worker test suite (77 tests)
- **Docker Containerization**: Consistent development and deployment environments
- **Code Quality**: Automated linting, formatting, and type checking

## Features

- **Internal API Service**: FastAPI-based REST API with PostgreSQL, MinIO, RabbitMQ, Vault, and Ollama integrations
- **Web Interface**: Modern FastAPI-based web application with Jinja2 templates
- **Worker Service**: Celery-based background task processing with scheduled, batch, and event-driven tasks
- **Task Monitoring**: Flower dashboard for real-time task monitoring and inspection
- Python 3.12 development environment
- Multi-service Docker infrastructure (nginx, PostgreSQL, RabbitMQ, MinIO, Vault, Ollama, n8n, Celery Worker, Beat, Flower)
- Comprehensive testing framework (pytest with coverage)
- Docker-based development workflow
- Enhanced Makefile with service management
- Type checking with mypy
- Code formatting with black
- Linting with ruff
- 100% test coverage enforcement

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Make installed (usually pre-installed on Unix systems)

### Initial Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd Odin
```

2. Configure environment variables (optional):
```bash
cp env.example .env
# Edit .env with your preferred settings
```

3. Build and start the development environment:
```bash
make setup
make up
```

4. Access the container shell:
```bash
make shell
```

5. Initialize services (optional):
```bash
# Initialize MinIO buckets
./scripts/init-minio.sh

# Check Vault status
./scripts/init-vault.sh
```

## Development Setup

### Project Structure

```
Odin/
├── src/              # Source code
├── tests/            # Test directory
│   ├── unit/         # Unit tests
│   ├── integration/  # Integration tests
│   └── regression/   # Regression tests
├── nginx/            # Nginx configuration
│   └── nginx.conf    # Reverse proxy configuration
├── scripts/          # Initialization scripts
│   ├── init-vault.sh # Vault initialization script
│   └── init-minio.sh # MinIO initialization script
├── .cursorrules      # Cursor AI development rules
├── Dockerfile        # Docker container definition
├── docker-compose.yml # Docker Compose configuration
├── env.example       # Environment variables template
├── Makefile          # Build automation
├── pyproject.toml    # Python project configuration
├── requirements.txt  # Production dependencies
└── requirements-dev.txt # Development dependencies
```

### Makefile Commands

The project uses a Makefile for common development tasks:

#### Setup and Docker Management
- `make setup` - Initial project setup (install dependencies)
- `make build` - Build Docker image
- `make up` - Start Docker containers
- `make down` - Stop Docker containers
- `make shell` - Access container shell
- `make services-up` - Start all services (nginx, postgresql, etc.)
- `make services-down` - Stop all services
- `make services-logs` - View logs from all services

#### Testing
- `make test` - Run all tests
- `make test-unit` - Run unit tests only
- `make test-integration` - Run integration tests only
- `make test-regression` - Run regression tests
- `make coverage` - Generate coverage report (HTML and terminal)

#### Code Quality
- `make lint` - Run linting (ruff)
- `make format` - Format code (black)
- `make type-check` - Run type checking (mypy)
- `make quality` - Run all quality checks (lint, type-check, format)
- `make test-full` - Run full test suite with coverage and quality checks

#### Web Application
- `make web-dev` - Start web server in development mode
- `make web-logs` - View web application logs
- `make web-shell` - Access web container shell
- `make web-test` - Run web application tests only

#### API Service
- `make api-dev` - Start API server in development mode
- `make api-logs` - View API service logs
- `make api-shell` - Access API container shell
- `make api-test` - Run API tests only
- `make api-health` - Check API health

#### Maintenance
- `make clean` - Clean build artifacts and cache files
- `make install` - Install package in development mode

### Development Workflow

1. **Start the development environment**:
   ```bash
   make up
   make shell
   ```

2. **Follow TDD workflow**:
   - Write a failing test first
   - Implement minimal code to pass
   - Refactor while keeping tests green

3. **Run tests**:
   ```bash
   make test          # All tests
   make test-unit     # Unit tests only
   make coverage      # With coverage report
   ```

4. **Check code quality**:
   ```bash
   make lint          # Check for linting issues
   make format        # Format code
   make type-check    # Verify type hints
   ```

5. **Clean up**:
   ```bash
   make clean         # Remove build artifacts
   ```

## Testing Guidelines

### Test Coverage Requirements

- **100% coverage is mandatory** for all code
- Coverage is enforced via pytest configuration
- Reports are generated in HTML (`htmlcov/index.html`) and terminal

### Test Organization

- **Unit Tests** (`tests/unit/`): Test individual components in isolation
- **Integration Tests** (`tests/integration/`): Test component interactions
- **Regression Tests** (`tests/regression/`): Prevent bugs from reoccurring

### Running Tests

```bash
# Run all tests
make test

# Run specific test types
make test-unit
make test-integration
make test-regression

# Generate coverage report
make coverage
```

### Writing Tests

- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`
- Mark tests appropriately:
  - `@pytest.mark.unit` for unit tests
  - `@pytest.mark.integration` for integration tests
  - `@pytest.mark.regression` for regression tests
- Use fixtures for common setup
- Mock external dependencies in unit tests

## Docker Services

The Odin development environment includes the following services:

### Service Overview

| Service | Port | Access URL | Description |
|---------|------|------------|-------------|
| **nginx** | 80 | http://localhost/ | Reverse proxy for all services |
| **Odin Web Portal** | internal | http://localhost/ | FastAPI web interface (via nginx) |
| **Odin API** | 8001 | http://api:8001 (internal) | Internal REST API service |
| **Celery Worker** | internal | N/A (internal) | Background task worker |
| **Celery Beat** | internal | N/A (internal) | Periodic task scheduler |
| **Flower** | 5555 | http://localhost/flower/ | Celery monitoring dashboard |
| **Ollama** | 11434 | http://localhost/ollama/ | AI/ML model server |
| **PostgreSQL** | 5432 | Direct connection | Relational database |
| **n8n** | 5678 | http://localhost/n8n/ | Workflow automation platform |
| **RabbitMQ** | 5672, 15672 | http://localhost/rabbitmq/ | Message broker with management UI |
| **Vault** | 8200 | http://localhost/vault/ | Secrets management |
| **MinIO** | 9000, 9001 | http://localhost/minio/ | S3-compatible object storage |

### Service Details

#### Nginx (Reverse Proxy)
- Entry point for all services
- Routes requests to appropriate backend services
- Health check endpoint: http://localhost/health

#### Odin Web Portal
- FastAPI-based web interface
- Jinja2 templating engine for HTML rendering
- Served at: http://localhost/ (root path via nginx)
- Built with TDD and SOLID principles
- Features: "Hello World" landing page with modern UI
- Container name: `portal`

#### Odin API Service
- Internal REST API for backend operations
- Accessible only within Docker network at: http://api:8001
- **Not exposed** through nginx (internal use only)
- Built with TDD and SOLID principles, 100% test coverage
- Container name: `odin-api`
- Features:
  - **Data Management**: CRUD operations
  - **File Storage**: MinIO integration for S3-compatible storage
  - **Message Queue**: RabbitMQ integration for async messaging
  - **Secret Management**: Vault integration for secure secrets
  - **LLM Operations**: Ollama integration for text generation
  - **Health Checks**: Service status monitoring
- Documentation: See `API_GUIDE.md` for detailed API documentation

#### Ollama
- AI/ML model server for running local LLMs
- Models stored in persistent volume
- Access via: http://localhost/ollama/

#### PostgreSQL
- Default database: `odin_db`
- Default user: `odin` (configurable via .env)
- Connection string: `postgresql://odin:odin_dev_password@postgresql:5432/odin_db`

#### n8n
- Workflow automation platform
- Uses PostgreSQL for data storage
- Default credentials: admin/admin (configurable via .env)
- Access via: http://localhost/n8n/

#### RabbitMQ
- Message broker for async task processing
- Management UI available
- Default credentials: odin/odin_dev_password (configurable via .env)
- Access via: http://localhost/rabbitmq/

#### HashiCorp Vault
- Secrets management system
- Running in dev mode (auto-unsealed)
- Root token: `dev-root-token` (configurable via .env)
- Access via: http://localhost/vault/

#### MinIO
- S3-compatible object storage
- Default credentials: minioadmin/minioadmin (configurable via .env)
- Console: http://localhost/minio/
- API: Access directly via `minio:9000` from within Docker network, or configure your application to use the service name

#### Celery Worker Service
- Background task processing with Celery
- Three components: Worker (execution), Beat (scheduling), Flower (monitoring)
- Uses RabbitMQ as message broker
- Uses PostgreSQL as result backend
- Task types: Scheduled, batch processing, event-driven
- Access Flower dashboard at: http://localhost/flower/ (admin/admin)
- See [WORKER_GUIDE.md](WORKER_GUIDE.md) for detailed documentation

### Docker Commands

```bash
# Build the image
make build

# Start all containers
make up

# Start only services (without app container)
make services-up

# Stop containers
make down

# Stop only services
make services-down

# View service logs
make services-logs

# Access container shell
make shell
```

### Environment Configuration

Copy `env.example` to `.env` and customize:
```bash
cp env.example .env
```

Key environment variables:
- `WEB_HOST`, `WEB_PORT`, `WEB_RELOAD`, `WEB_LOG_LEVEL` - Web application configuration
- `API_HOST`, `API_PORT`, `API_RELOAD`, `API_LOG_LEVEL` - API service configuration
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` - PostgreSQL configuration
- `POSTGRES_DSN` - Full PostgreSQL connection string (for API)
- `N8N_USER`, `N8N_PASSWORD` - n8n credentials
- `RABBITMQ_USER`, `RABBITMQ_PASSWORD` - RabbitMQ credentials
- `RABBITMQ_URL` - Full RabbitMQ connection URL (for API)
- `VAULT_ROOT_TOKEN`, `VAULT_ADDR` - Vault configuration
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_ENDPOINT` - MinIO credentials
- `OLLAMA_BASE_URL` - Ollama API base URL

### Volume Mounts

- **Project directory**: Mounted in app container for live code editing
- **PostgreSQL data**: Persistent volume `postgresql-data`
- **n8n workflows**: Persistent volume `n8n-data`
- **RabbitMQ data**: Persistent volume `rabbitmq-data`
- **Vault data**: Persistent volumes `vault-data` and `vault-logs`
- **MinIO data**: Persistent volume `minio-data`
- **Ollama models**: Persistent volume `ollama-models`

### Service Initialization

After starting services, you may want to initialize them:

```bash
# Initialize MinIO buckets
./scripts/init-minio.sh

# Check Vault status
./scripts/init-vault.sh
```

## Code Quality Tools

### Black (Code Formatting)
- Line length: 100 characters
- Automatic formatting on save (if configured)
- Run manually: `make format`

### Ruff (Linting)
- Fast Python linter
- Catches common errors and style issues
- Run manually: `make lint`

### MyPy (Type Checking)
- Static type checking
- Strict mode enabled
- Run manually: `make type-check`

### Pytest (Testing)
- Test framework with plugins:
  - `pytest-cov`: Coverage reporting
  - `pytest-mock`: Mocking utilities
  - `pytest-asyncio`: Async test support

## Configuration Files

### `pyproject.toml`
- Project metadata and dependencies
- Tool configurations (pytest, black, ruff, mypy)
- Coverage settings (100% threshold)

### `.cursorrules`
- Cursor AI development guidelines
- TDD workflow enforcement
- SOLID principles reminders
- Best practices checklist

## Contributing

### Development Standards

1. **Write tests first** (TDD)
2. **Follow SOLID principles**
3. **Maintain 100% test coverage**
4. **Use type hints** for all functions
5. **Write docstrings** for all public functions/classes
6. **Run quality checks** before committing:
   ```bash
   make quality
   make test-full
   ```

### Pre-Commit Checklist

- [ ] All tests pass
- [ ] 100% test coverage achieved
- [ ] Type hints added
- [ ] Docstrings added
- [ ] Code formatted (`make format`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make type-check`)

## License

MIT License

## Author

Nicolas Lallier
