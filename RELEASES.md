# Release Notes

## Version 0.1.0 - Multi-Service Docker Infrastructure

**Release Date**: 2025-11-22  
**Status**: Released

### Overview

Major infrastructure update adding comprehensive multi-service Docker environment with nginx reverse proxy, PostgreSQL, RabbitMQ, MinIO, Vault, Ollama, and n8n. Significantly enhanced Makefile with improved commands, service management, and developer experience features.

### Features

#### Infrastructure Services
- **nginx** - Reverse proxy routing to all services with health check endpoint
- **Ollama** - AI/ML model server for local LLM hosting
- **PostgreSQL 16** - Primary relational database with persistent storage
- **n8n** - Workflow automation platform integrated with PostgreSQL
- **RabbitMQ** - Message broker with management UI
- **HashiCorp Vault** - Secrets management running in dev mode
- **MinIO** - S3-compatible object storage with console interface

#### Service Configuration
- All services connected via dedicated Docker network (`odin-network`)
- Persistent volumes for all stateful services
- Health checks configured for database and message queue
- Environment-based configuration via `.env` file
- Service dependencies properly configured

#### Nginx Reverse Proxy
- Routes to all services under single entry point (http://localhost/)
- Service endpoints:
  - `/health` - Health check
  - `/ollama/` - Ollama AI service
  - `/n8n/` - n8n workflow automation
  - `/rabbitmq/` - RabbitMQ management UI
  - `/vault/` - Vault web interface
  - `/minio/` - MinIO console
- WebSocket support for real-time services
- Configurable proxy settings

#### Initialization Scripts
- `scripts/init-vault.sh` - Vault initialization and status check
- `scripts/init-minio.sh` - MinIO bucket creation (requires mc client)
- Both scripts executable and documented

#### Enhanced Makefile
**Visual Improvements:**
- Color-coded output (green, yellow, blue, red)
- Organized sections with headers
- Beautiful help menu with emojis
- Better error messaging

**New Commands:**
- `make init-env` - Create .env from template
- `make init-services` - Initialize Vault and MinIO
- `make rebuild` - Rebuild without cache
- `make ps` - Show running containers
- `make logs` - View all container logs
- `make restart` - Restart all containers
- `make test-watch` - Run tests in watch mode
- `make check-all` - Run all checks (tests + quality + coverage)
- `make services-status` - Show service status
- `make services-health` - Check health of all services
- `make db-shell` - Access PostgreSQL shell
- `make db-migrate` - Database migration placeholder
- `make db-reset` - Reset database with confirmation
- `make backup` - Backup PostgreSQL database
- `make restore` - Restore from backup
- `make docker-prune` - Clean unused Docker resources
- `make docker-clean` - Deep clean with confirmation

**Enhanced Commands:**
- Improved setup workflow with automatic .env creation
- Better service management with status checking
- Interactive confirmations for destructive operations
- Comprehensive health checks for all services

#### Environment Configuration
- `env.example` - Template for environment variables
- Default credentials for all services
- Configurable service ports and settings
- PostgreSQL, n8n, RabbitMQ, Vault, and MinIO configurations

#### Documentation
- Comprehensive service documentation in README
- Service access URLs and ports table
- Connection strings for database access
- Service initialization instructions
- Updated project structure documentation
- Enhanced Makefile command reference

### Configuration Details

#### Service Ports
- nginx: 80 (HTTP)
- Ollama: 11434 (internal)
- PostgreSQL: 5432 (internal)
- n8n: 5678 (internal)
- RabbitMQ: 5672 (AMQP), 15672 (Management UI)
- Vault: 8200 (internal)
- MinIO: 9000 (API), 9001 (Console)

#### Default Credentials (Development)
- PostgreSQL: odin/odin_dev_password
- n8n: admin/admin
- RabbitMQ: odin/odin_dev_password
- Vault: dev-root-token
- MinIO: minioadmin/minioadmin

#### Persistent Volumes
- `postgresql-data` - PostgreSQL database
- `n8n-data` - n8n workflows and settings
- `rabbitmq-data` - RabbitMQ messages and config
- `vault-data` and `vault-logs` - Vault storage
- `minio-data` - MinIO object storage
- `ollama-models` - Ollama AI models

### Technical Improvements

#### Docker Compose
- Updated to remove deprecated `version` field
- Service dependencies configured with health conditions
- Proper network isolation
- Resource management ready

#### Dockerfile
- Fixed build issues with src/ directory copy order
- README.md now copied before pip install
- Both development and production stages updated
- Optimized layer caching

#### pyproject.toml
- Version updated to 0.1.0
- Removed deprecated license classifier
- Updated to use SPDX license expression

### Breaking Changes

- None - All changes are additive

### Migration from 0.0.0 to 0.1.0

1. Pull latest changes
2. Run `make rebuild` to rebuild Docker images
3. Copy `env.example` to `.env` and customize if needed
4. Run `make services-up` to start all services
5. Run `make init-services` to initialize Vault and MinIO
6. Verify services with `make services-health`

### Known Limitations

- MinIO `mc` client required for bucket initialization script
- Services run in development mode (not production-ready)
- Vault runs in dev mode (data not persisted on restart)
- No SSL/TLS configuration yet

### Future Enhancements

- SSL/TLS certificate management
- Production-ready service configurations
- Automated backup scheduling
- Service monitoring and alerting
- CI/CD pipeline integration
- Database migration framework

### Security Notes

- **WARNING**: Default credentials are for development only
- Change all passwords before production use
- Vault dev mode is NOT secure for production
- All services accessible without authentication
- Network isolation within Docker, but ports exposed on localhost

### Contributors

- Nicolas Lallier - Infrastructure setup and configuration

---

## Version 0.0.0 - Initial Development Environment Setup

**Release Date**: 2025-11-22  
**Status**: Released  
**Commit**: e9d817f

### Overview

Initial release establishing the Python development environment with comprehensive tooling for Test-Driven Development (TDD), SOLID principles adherence, and 100% test coverage requirements.

### Features

#### Development Environment
- **Python 3.12** base environment
- **Docker** containerization for consistent development and deployment
- **Docker Compose** orchestration for easy container management
- Multi-stage Dockerfile supporting both development and production builds

#### Testing Framework
- **pytest 8.0+** as the primary testing framework
- **pytest-cov** for code coverage reporting with 100% threshold enforcement
- **pytest-mock** for advanced mocking capabilities
- **pytest-asyncio** for async/await test support
- Organized test structure:
  - Unit tests (`tests/unit/`)
  - Integration tests (`tests/integration/`)
  - Regression tests (`tests/regression/`)
- Coverage reports in HTML, XML, and terminal formats

#### Code Quality Tools
- **black** for automatic code formatting (100 character line length)
- **ruff** for fast linting and code quality checks
- **mypy** for static type checking with strict mode
- **pylint** for additional code analysis

#### Build Automation
- **Makefile** with comprehensive command set:
  - Setup and Docker management (`setup`, `build`, `up`, `down`, `shell`)
  - Testing commands (`test`, `test-unit`, `test-integration`, `test-regression`, `coverage`)
  - Code quality checks (`lint`, `format`, `type-check`, `quality`)
  - Maintenance (`clean`, `install`)

#### Project Configuration
- **pyproject.toml** with:
  - Project metadata and dependencies
  - pytest configuration with 100% coverage threshold
  - Tool configurations (black, ruff, mypy, pylint)
  - Coverage exclusion patterns
- **requirements.txt** for production dependencies
- **requirements-dev.txt** for development dependencies

#### Development Guidelines
- **.cursorrules** file enforcing:
  - Test-Driven Development (TDD) workflow
  - SOLID principles adherence
  - 100% test coverage mandate
  - Type hints requirements
  - Documentation standards
  - Code quality best practices

#### Project Structure
- Organized source code directory (`src/`)
- Comprehensive test directory structure
- Configuration files for all development tools
- Docker and Git ignore files

### Configuration Details

#### Test Coverage
- **100% coverage threshold** enforced via pytest configuration
- Coverage reports generated automatically
- HTML coverage reports available in `htmlcov/`
- Terminal and XML reports for CI/CD integration

#### Type Checking
- Strict mypy configuration
- Type hints required for all functions
- Forward reference support via `from __future__ import annotations`

#### Code Formatting
- Black formatter with 100 character line length
- Consistent code style enforcement
- Integration with pre-commit workflows

#### Linting
- Ruff configured with comprehensive rule set
- Pycodestyle, Pyflakes, and additional plugins
- Per-file ignore patterns for common exceptions

### Docker Configuration

#### Development Container
- Python 3.12 slim base image
- Development dependencies pre-installed
- Volume mounts for live code editing
- Interactive shell access

#### Production Container
- Optimized multi-stage build
- Production dependencies only
- Minimal image size

### Dependencies

#### Development Dependencies
- pytest>=8.0.0
- pytest-cov>=4.1.0
- pytest-mock>=3.12.0
- pytest-asyncio>=0.23.0
- black>=24.0.0
- ruff>=0.1.0
- mypy>=1.8.0
- pylint>=3.0.0

#### Production Dependencies
- (To be added as project develops)

### Documentation

- Comprehensive README with:
  - Quick start guide
  - Development workflow instructions
  - Testing guidelines
  - Docker usage instructions
  - Makefile command reference
  - Contributing guidelines

### Known Limitations

- Initial setup - no application code yet
- Production dependencies to be added as project develops
- CI/CD pipeline configuration pending

### Future Enhancements

- CI/CD pipeline integration
- Pre-commit hooks configuration
- Additional development tools as needed
- Application-specific features

### Migration Notes

N/A - Initial release

### Breaking Changes

N/A - Initial release

### Deprecations

N/A - Initial release

### Security Notes

- Docker images use official Python base images
- Dependencies are pinned to specific versions
- No known security vulnerabilities in initial setup

### Contributors

- Nicolas Lallier - Initial setup and configuration

---

**Note**: This is the initial development environment setup. Application-specific features and code will be added in subsequent releases following TDD and SOLID principles.

