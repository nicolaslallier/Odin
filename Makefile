.PHONY: help setup build rebuild up down restart ps logs shell install clean \
        test test-unit test-integration test-regression test-watch coverage \
        test-api test-api-unit test-api-integration coverage-api \
        test-web test-web-unit test-web-integration coverage-web \
        test-worker test-worker-unit test-worker-integration coverage-worker \
        lint format type-check quality check-all \
        services-up services-down services-restart services-logs services-status services-health \
        web-dev web-logs web-shell web-test \
        api-dev api-logs api-shell api-test api-health \
        worker-dev worker-logs worker-shell worker-test worker-status \
        beat-start beat-logs flower-start flower-logs \
        db-shell db-migrate db-reset \
        init-env init-services backup restore \
        docker-prune docker-clean

# Color output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Variables
DOCKER_COMPOSE = docker-compose
DOCKER = docker
PYTHON = python
CONTAINER_NAME = portal
SERVICES = nginx ollama postgresql n8n rabbitmq vault minio

# Default target
.DEFAULT_GOAL := help

# Help target with improved formatting
help:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)                    Odin Development Environment                       $(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(GREEN)📦 Setup & Build:$(NC)"
	@echo "  make setup           - Initial project setup (build + install dependencies)"
	@echo "  make build           - Build Docker images"
	@echo "  make rebuild         - Rebuild Docker images (no cache)"
	@echo "  make init-env        - Create .env file from env.example"
	@echo "  make init-services   - Initialize services (Vault, MinIO buckets)"
	@echo ""
	@echo "$(GREEN)🚀 Container Management:$(NC)"
	@echo "  make up              - Start all containers (infra + ALL API microservices)"
	@echo "  make down            - Stop all containers"
	@echo "  make restart         - Restart all containers"
	@echo "  make ps              - Show running containers"
	@echo "  make logs            - View logs from all containers"
	@echo "  make shell           - Access portal container shell (keeps web server running)"
	@echo "  make shell-dev       - Start portal in interactive shell mode (no web server)"
	@echo ""
	@echo "$(GREEN)🔧 API Microservices:$(NC)"
	@echo "  ./scripts/list-api-services.sh     - Show all API microservice status"
	@echo "  ./scripts/start-api-service.sh <n> - Start specific microservice"
	@echo "  ./scripts/stop-api-service.sh <n>  - Stop specific microservice"
	@echo "  See MICROSERVICES_GUIDE.md for details"
	@echo ""
	@echo "$(GREEN)🧪 Testing (All Components):$(NC)"
	@echo "  make test            - Run all tests (all components)"
	@echo "  make test-unit       - Run unit tests only (all components)"
	@echo "  make test-integration - Run integration tests only (all components)"
	@echo "  make test-regression - Run regression tests only"
	@echo "  make test-services   - Run service accessibility tests"
	@echo "  make test-watch      - Run tests in watch mode"
	@echo "  make coverage        - Generate coverage report (HTML + terminal)"
	@echo ""
	@echo "$(GREEN)🧪 Component-Specific Testing:$(NC)"
	@echo "  make test-api        - Run all API tests (unit + integration)"
	@echo "  make test-api-unit   - Run API unit tests only"
	@echo "  make test-api-integration - Run API integration tests only"
	@echo "  make coverage-api    - Generate API coverage report"
	@echo "  make test-web        - Run all Web tests (unit + integration)"
	@echo "  make test-web-unit   - Run Web unit tests only"
	@echo "  make test-web-integration - Run Web integration tests only"
	@echo "  make coverage-web    - Generate Web coverage report"
	@echo "  make test-worker     - Run all Worker tests (unit + integration)"
	@echo "  make test-worker-unit - Run Worker unit tests only"
	@echo "  make test-worker-integration - Run Worker integration tests only"
	@echo "  make coverage-worker - Generate Worker coverage report"
	@echo "  make check-services  - Check which services are accessible (diagnostic)"
	@echo ""
	@echo "$(GREEN)🔍 Code Quality:$(NC)"
	@echo "  make lint            - Run linting (ruff)"
	@echo "  make format          - Format code (black)"
	@echo "  make type-check      - Run type checking (mypy)"
	@echo "  make quality         - Run all quality checks (lint + type + format)"
	@echo "  make check-all       - Run all checks (tests + quality + coverage)"
	@echo ""
	@echo "$(GREEN)🛠️  Service Management:$(NC)"
	@echo "  make services-up     - Start all services (nginx, postgresql, etc.)"
	@echo "  make services-down   - Stop all services"
	@echo "  make services-restart - Restart all services"
	@echo "  make services-logs   - View logs from all services"
	@echo "  make services-status - Show service status"
	@echo "  make services-health - Check service health"
	@echo ""
	@echo "$(GREEN)🌐 Web Application:$(NC)"
	@echo "  make web-dev         - Start web server in development mode"
	@echo "  make web-logs        - View web application logs"
	@echo "  make web-shell       - Access web container shell"
	@echo "  make web-test        - Run web application tests only"
	@echo ""
	@echo "$(GREEN)⚙️  API Service:$(NC)"
	@echo "  make api-dev         - Start API server in development mode"
	@echo "  make api-logs        - View API service logs"
	@echo "  make api-shell       - Access API container shell"
	@echo "  make api-test        - Run API tests only (alias for test-api)"
	@echo "  make api-health      - Check API health"
	@echo ""
	@echo "$(GREEN)⚡ Worker Service:$(NC)"
	@echo "  make worker-dev      - Start Worker in development mode"
	@echo "  make worker-logs     - View Worker service logs"
	@echo "  make worker-shell    - Access Worker container shell"
	@echo "  make worker-test     - Run Worker tests only (alias for test-worker)"
	@echo "  make worker-status   - Check worker, beat, and flower status"
	@echo "  make beat-start      - Start Celery Beat scheduler"
	@echo "  make beat-logs       - View Celery Beat logs"
	@echo "  make flower-start    - Start Flower monitoring dashboard"
	@echo "  make flower-logs     - View Flower logs"
	@echo ""
	@echo "$(GREEN)🗄️  Database:$(NC)"
	@echo "  make db-shell        - Access PostgreSQL shell"
	@echo "  make db-migrate      - Run database migrations (placeholder)"
	@echo "  make db-reset        - Reset database (WARNING: deletes all data)"
	@echo ""
	@echo "$(GREEN)🧹 Cleanup:$(NC)"
	@echo "  make clean           - Clean build artifacts and cache"
	@echo "  make docker-prune    - Prune Docker system (containers, images, volumes)"
	@echo "  make docker-clean    - Deep clean (stop all, remove volumes, prune)"
	@echo ""
	@echo "$(GREEN)💾 Backup & Restore:$(NC)"
	@echo "  make backup          - Backup PostgreSQL database"
	@echo "  make restore         - Restore PostgreSQL database from backup"
	@echo ""
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(YELLOW)💡 Tip: Run 'make up' to start everything (infra + all API microservices)$(NC)"
	@echo "$(YELLOW)💡 Tip: Run './scripts/list-api-services.sh' to check microservice status$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"

# ============================================================================
# Setup & Build
# ============================================================================

# Initial project setup
setup: build init-env
	@echo "$(GREEN)✓ Setting up development environment...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pip install -r requirements-dev.txt
	@echo "$(GREEN)✓ Setup complete!$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Edit .env with your configuration"
	@echo "  2. Run 'make up' to start all services"
	@echo "  3. Access portal at: http://localhost/"

# Build Docker images
build:
	@echo "$(GREEN)Building Docker images...$(NC)"
	@$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✓ Build complete!$(NC)"

# Rebuild without cache
rebuild:
	@echo "$(YELLOW)Rebuilding Docker images (no cache)...$(NC)"
	@$(DOCKER_COMPOSE) build --no-cache
	@echo "$(GREEN)✓ Rebuild complete!$(NC)"

# Initialize environment file
init-env:
	@if [ ! -f .env ]; then \
		echo "$(GREEN)Creating .env file from env.example...$(NC)"; \
		cp env.example .env; \
		echo "$(GREEN)✓ .env file created!$(NC)"; \
		echo "$(YELLOW)⚠ Please edit .env with your configuration$(NC)"; \
	else \
		echo "$(YELLOW)⚠ .env file already exists, skipping...$(NC)"; \
	fi

# Initialize services (Vault, MinIO)
init-services:
	@echo "$(GREEN)Initializing services...$(NC)"
	@if [ -f ./scripts/init-postgresql.sh ]; then \
		echo "$(BLUE)Initializing PostgreSQL...$(NC)"; \
		./scripts/init-postgresql.sh; \
	fi
	@if [ -f ./scripts/init-vault.sh ]; then \
		echo "$(BLUE)Initializing Vault...$(NC)"; \
		./scripts/init-vault.sh; \
	fi
	@if [ -f ./scripts/init-minio.sh ]; then \
		echo "$(BLUE)Initializing MinIO...$(NC)"; \
		./scripts/init-minio.sh; \
	fi
	@echo "$(GREEN)✓ Services initialized!$(NC)"

# ============================================================================
# Container Management
# ============================================================================

# Start all containers (including all API microservices)
up:
	@echo "$(GREEN)Starting all containers (infrastructure + all API microservices)...$(NC)"
	@$(DOCKER_COMPOSE) --profile all up -d
	@echo "$(GREEN)✓ Containers started!$(NC)"
	@echo "$(YELLOW)Use 'make ps' to see running containers$(NC)"
	@echo "$(YELLOW)Use './scripts/list-api-services.sh' to check API microservice status$(NC)"
	@echo "$(YELLOW)Use 'make shell' to access the app container$(NC)"

# Stop all containers
down:
	@echo "$(YELLOW)Stopping all containers...$(NC)"
	@$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Containers stopped!$(NC)"

# Restart all containers
restart:
	@echo "$(YELLOW)Restarting all containers (full cycle: down, then up with all profiles)...$(NC)"
	@$(DOCKER_COMPOSE) down
	@$(DOCKER_COMPOSE) --profile all up -d
	@echo "$(GREEN)✓ Containers fully restarted!$(NC)"

# Show running containers
ps:
	@echo "$(BLUE)Running containers:$(NC)"
	@$(DOCKER_COMPOSE) ps

# View logs
logs:
	@echo "$(BLUE)Viewing logs (Ctrl+C to exit)...$(NC)"
	@$(DOCKER_COMPOSE) logs -f

# Access app container shell (portal will keep running)
shell:
	@echo "$(GREEN)Accessing portal container shell...$(NC)"
	@$(DOCKER_COMPOSE) exec portal /bin/bash

# Start portal in interactive mode (shell instead of web server)
shell-dev:
	@echo "$(GREEN)Starting portal in development shell mode...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml run --rm portal /bin/bash

# ============================================================================
# Testing
# ============================================================================

# Run all tests
test:
	@echo "$(BLUE)Running all API microservice tests by component...$(NC)"
	@$(MAKE) test-api-confluence
	@$(MAKE) test-api-files
	@$(MAKE) test-api-llm
	@$(MAKE) test-api-health
	@$(MAKE) test-api-logs
	@$(MAKE) test-api-data
	@$(MAKE) test-api-secrets
	@$(MAKE) test-api-messages
	@$(MAKE) test-api-image-analysis
	@echo "$(GREEN)✓ All API microservice tests complete!$(NC)"

# Run unit tests only
test-unit:
	@echo "$(BLUE)Running unit tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/unit/ -v -m unit
	@echo "$(GREEN)✓ Unit tests complete!$(NC)"

# Run integration tests only
test-integration:
	@echo "$(BLUE)Running integration tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/integration/ -v -m integration
	@echo "$(GREEN)✓ Integration tests complete!$(NC)"

# Run regression tests
test-regression:
	@echo "$(BLUE)Running regression tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/regression/ -v -m regression
	@echo "$(GREEN)✓ Regression tests complete!$(NC)"

# Run service accessibility regression tests
test-services:
	@echo "$(BLUE)Running service accessibility tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/regression/test_service_accessibility.py -v
	@echo "$(GREEN)✓ Service accessibility tests complete!$(NC)"

# Check service accessibility (diagnostic tool)
check-services:
	@echo "$(BLUE)Checking service accessibility...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal python scripts/check-services.py

# Run tests in watch mode
test-watch:
	@echo "$(BLUE)Running tests in watch mode (Ctrl+C to exit)...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest-watch tests/ -v

# Generate coverage report
coverage:
	@echo "$(BLUE)Generating coverage report...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/ --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "$(GREEN)✓ Coverage report generated!$(NC)"
	@echo "$(YELLOW)HTML report: htmlcov/index.html$(NC)"

# ============================================================================
# Component-Specific Testing
# ============================================================================

# API Component Tests
# Run API tests with coverage (async cleanup warnings at end are harmless)
test-api:
	@echo "$(BLUE)Running all API tests (unit + integration, with coverage)...$(NC)"
	-@PYTHONWARNINGS="ignore" $(DOCKER_COMPOSE) exec api bash -c "cd /app && pytest -p no:warnings --log-cli-level=CRITICAL --tb=short tests/unit/api/ tests/integration/api/ \
		--cov=src/api --cov-report=term-missing --cov-report=xml --cov-fail-under=70" || true
	@echo "$(GREEN)✓ API tests complete!$(NC)"

test-api-unit:
	@echo "$(BLUE)Running API unit tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/unit/api/ -v -m unit
	@echo "$(GREEN)✓ API unit tests complete!$(NC)"

test-api-integration:
	@echo "$(BLUE)Running API integration tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/integration/api/ -v -m integration
	@echo "$(GREEN)✓ API integration tests complete!$(NC)"

# Web Component Tests
test-web:
	@echo "$(BLUE)Running all Web tests (unit + integration)...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal bash -c "pytest tests/unit/web/ tests/integration/web/ -v \
		--cov=src --cov-report=term-missing:skip-covered --cov-report=html --cov-report=xml \
		--cov-fail-under=100"
	@echo "$(GREEN)✓ Web tests complete!$(NC)"

test-web-unit:
	@echo "$(BLUE)Running Web unit tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/unit/web/ -v -m unit
	@echo "$(GREEN)✓ Web unit tests complete!$(NC)"

test-web-integration:
	@echo "$(BLUE)Running Web integration tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/integration/web/ -v -m integration
	@echo "$(GREEN)✓ Web integration tests complete!$(NC)"

# Worker Component Tests
test-worker:
	@echo "$(BLUE)Running all Worker tests (unit + integration)...$(NC)"
	@$(DOCKER_COMPOSE) run --rm -e CELERY_BROKER_URL=amqp://$${RABBITMQ_USER:-odin}:$${RABBITMQ_PASSWORD:-odin_dev_password}@rabbitmq:5672// -e CELERY_RESULT_BACKEND=db+postgresql://$${POSTGRES_USER:-odin}:$${POSTGRES_PASSWORD:-odin_dev_password}@postgresql:5432/$${POSTGRES_DB:-odin_db} portal pytest tests/unit/worker/ tests/integration/worker/ -v --no-cov
	@echo "$(GREEN)✓ Worker tests complete!$(NC)"

test-worker-unit:
	@echo "$(BLUE)Running Worker unit tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm -e CELERY_BROKER_URL=amqp://$${RABBITMQ_USER:-odin}:$${RABBITMQ_PASSWORD:-odin_dev_password}@rabbitmq:5672// -e CELERY_RESULT_BACKEND=db+postgresql://$${POSTGRES_USER:-odin}:$${POSTGRES_PASSWORD:-odin_dev_password}@postgresql:5432/$${POSTGRES_DB:-odin_db} portal pytest tests/unit/worker/ -v -m unit --no-cov
	@echo "$(GREEN)✓ Worker unit tests complete!$(NC)"

test-worker-integration:
	@echo "$(BLUE)Running Worker integration tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm -e CELERY_BROKER_URL=amqp://$${RABBITMQ_USER:-odin}:$${RABBITMQ_PASSWORD:-odin_dev_password}@rabbitmq:5672// -e CELERY_RESULT_BACKEND=db+postgresql://$${POSTGRES_USER:-odin}:$${POSTGRES_PASSWORD:-odin_dev_password}@postgresql:5432/$${POSTGRES_DB:-odin_db} portal pytest tests/integration/worker/ -v -m integration --no-cov
	@echo "$(GREEN)✓ Worker integration tests complete!$(NC)"

# Component-Specific Coverage
coverage-api:
	@echo "$(BLUE)Generating API coverage report...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/unit/api/ tests/integration/api/ --cov=src/api --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "$(GREEN)✓ API coverage report generated!$(NC)"
	@echo "$(YELLOW)HTML report: htmlcov/index.html$(NC)"

coverage-web:
	@echo "$(BLUE)Generating Web coverage report...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/unit/web/ tests/integration/web/ --cov=src/web --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "$(GREEN)✓ Web coverage report generated!$(NC)"
	@echo "$(YELLOW)HTML report: htmlcov/index.html$(NC)"

coverage-worker:
	@echo "$(BLUE)Generating Worker coverage report...$(NC)"
	@$(DOCKER_COMPOSE) run --rm -e CELERY_BROKER_URL=amqp://$${RABBITMQ_USER:-odin}:$${RABBITMQ_PASSWORD:-odin_dev_password}@rabbitmq:5672// -e CELERY_RESULT_BACKEND=db+postgresql://$${POSTGRES_USER:-odin}:$${POSTGRES_PASSWORD:-odin_dev_password}@postgresql:5432/$${POSTGRES_DB:-odin_db} portal pytest tests/unit/worker/ tests/integration/worker/ --cov=src/worker --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "$(GREEN)✓ Worker coverage report generated!$(NC)"
	@echo "$(YELLOW)HTML report: htmlcov/index.html$(NC)"

# ============================================================================
# Code Quality
# ============================================================================

# Run linting
lint:
	@echo "$(BLUE)Running linter (ruff)...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal ruff check src/ tests/
	@echo "$(GREEN)✓ Linting complete!$(NC)"

# Format code
format:
	@echo "$(BLUE)Formatting code with black...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal black src/ tests/
	@echo "$(GREEN)✓ Formatting complete!$(NC)"

# Type checking
type-check:
	@echo "$(BLUE)Running type checker (mypy)...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal mypy src/
	@echo "$(GREEN)✓ Type checking complete!$(NC)"

# Quality check (runs all quality checks)
quality: lint type-check format
	@echo "$(GREEN)✓ All quality checks complete!$(NC)"

# Run all checks (tests + coverage + quality)
check-all: coverage quality
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)✓ All checks passed successfully!$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"

# Install package in development mode
install:
	@echo "$(BLUE)Installing package in development mode...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pip install -e .
	@echo "$(GREEN)✓ Installation complete!$(NC)"

# ============================================================================
# Cleanup
# ============================================================================

# Clean build artifacts
clean:
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*.pyd" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -r {} + 2>/dev/null || true
	@rm -rf build/ dist/ .coverage htmlcov/ coverage.xml .tox/ .nox/ 2>/dev/null || true
	@echo "$(GREEN)✓ Clean complete!$(NC)"

# Prune Docker system
docker-prune:
	@echo "$(YELLOW)⚠ This will remove unused Docker containers, networks, and images$(NC)"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW)Pruning Docker system...$(NC)"; \
		$(DOCKER) system prune -f; \
		echo "$(GREEN)✓ Docker prune complete!$(NC)"; \
	else \
		echo "$(RED)Cancelled.$(NC)"; \
	fi

# Deep clean (stop all, remove volumes, prune)
docker-clean: down
	@echo "$(RED)⚠ WARNING: This will remove ALL Docker volumes and data$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW)Removing volumes...$(NC)"; \
		$(DOCKER_COMPOSE) down -v; \
		$(DOCKER) system prune -af --volumes; \
		echo "$(GREEN)✓ Deep clean complete!$(NC)"; \
	else \
		echo "$(RED)Cancelled.$(NC)"; \
	fi

# ============================================================================
# Service Management
# ============================================================================

# Start all services
services-up:
	@echo "$(GREEN)Starting all services...$(NC)"
	@$(DOCKER_COMPOSE) up -d $(SERVICES)
	@echo "$(GREEN)✓ Services started!$(NC)"
	@echo ""
	@echo "$(BLUE)Access services at:$(NC)"
	@echo "  $(YELLOW)→$(NC) Nginx (reverse proxy): http://localhost/"
	@echo "  $(YELLOW)→$(NC) Ollama:               http://localhost/ollama/"
	@echo "  $(YELLOW)→$(NC) n8n:                  http://localhost/n8n/"
	@echo "  $(YELLOW)→$(NC) RabbitMQ:             http://localhost/rabbitmq/"
	@echo "  $(YELLOW)→$(NC) Vault:                http://localhost/vault/"
	@echo "  $(YELLOW)→$(NC) MinIO:                http://localhost/minio/"
	@echo ""
	@echo "$(YELLOW)💡 Run 'make services-health' to check service status$(NC)"

# Stop all services
services-down:
	@echo "$(YELLOW)Stopping all services...$(NC)"
	@$(DOCKER_COMPOSE) stop $(SERVICES)
	@echo "$(GREEN)✓ Services stopped!$(NC)"

# Restart all services
services-restart: services-down services-up
	@echo "$(GREEN)✓ Services restarted!$(NC)"

# View service logs
services-logs:
	@echo "$(BLUE)Viewing service logs (Ctrl+C to exit)...$(NC)"
	@$(DOCKER_COMPOSE) logs -f $(SERVICES)

# Show service status
services-status:
	@echo "$(BLUE)Service Status:$(NC)"
	@$(DOCKER_COMPOSE) ps $(SERVICES)

# Check service health
services-health:
	@echo "$(BLUE)Checking service health...$(NC)"
	@echo ""
	@echo "$(GREEN)Nginx:$(NC)"
	@curl -sf http://localhost/health > /dev/null && echo "  $(GREEN)✓ Healthy$(NC)" || echo "  $(RED)✗ Unhealthy$(NC)"
	@echo ""
	@echo "$(GREEN)PostgreSQL:$(NC)"
	@$(DOCKER_COMPOSE) exec -T postgresql pg_isready -U odin > /dev/null 2>&1 && echo "  $(GREEN)✓ Healthy$(NC)" || echo "  $(RED)✗ Unhealthy$(NC)"
	@echo ""
	@echo "$(GREEN)RabbitMQ:$(NC)"
	@$(DOCKER_COMPOSE) exec -T rabbitmq rabbitmq-diagnostics ping > /dev/null 2>&1 && echo "  $(GREEN)✓ Healthy$(NC)" || echo "  $(RED)✗ Unhealthy$(NC)"
	@echo ""
	@echo "$(GREEN)MinIO:$(NC)"
	@curl -sf http://localhost:9000/minio/health/live > /dev/null && echo "  $(GREEN)✓ Healthy$(NC)" || echo "  $(RED)✗ Unhealthy$(NC)"
	@echo ""
	@echo "$(GREEN)Vault:$(NC)"
	@curl -sf http://localhost:8200/v1/sys/health > /dev/null && echo "  $(GREEN)✓ Healthy$(NC)" || echo "  $(RED)✗ Unhealthy$(NC)"

# ============================================================================
# Web Application
# ============================================================================

# Start web server in development mode
web-dev:
	@echo "$(GREEN)Starting web server in development mode...$(NC)"
	@echo "$(YELLOW)Access at: http://localhost/ (via nginx)$(NC)"
	@$(DOCKER_COMPOSE) up portal

# View web application logs
web-logs:
	@echo "$(BLUE)Viewing web application logs (Ctrl+C to exit)...$(NC)"
	@$(DOCKER_COMPOSE) logs -f portal

# Access web container shell
web-shell:
	@echo "$(GREEN)Accessing web container shell...$(NC)"
	@$(DOCKER_COMPOSE) exec portal /bin/bash || $(DOCKER_COMPOSE) run --rm portal /bin/bash

# Run web application tests only (alias for test-web)
web-test: test-web

# ============================================================================
# API Service
# ============================================================================

# Start API server in development mode
api-dev:
	@echo "$(GREEN)Starting API server in development mode...$(NC)"
	@echo "$(YELLOW)API is internal only, accessible at: http://api:8001 (from within Docker network)$(NC)"
	@$(DOCKER_COMPOSE) up api

# View API service logs
api-logs:
	@echo "$(BLUE)Viewing API service logs (Ctrl+C to exit)...$(NC)"
	@$(DOCKER_COMPOSE) logs -f api

# Access API container shell
api-shell:
	@echo "$(GREEN)Accessing API container shell...$(NC)"
	@$(DOCKER_COMPOSE) exec api /bin/bash || $(DOCKER_COMPOSE) run --rm api /bin/bash

# Run API tests only (alias for test-api)
api-test: test-api

# Check API health
api-health:
	@echo "$(BLUE)Checking API health...$(NC)"
	@$(DOCKER_COMPOSE) exec api curl -f http://localhost:8001/health || echo "$(RED)API is not responding$(NC)"

# ============================================================================
# Worker Service
# ============================================================================

# Start worker in development mode
worker-dev:
	@echo "$(GREEN)Starting Worker in development mode...$(NC)"
	@echo "$(YELLOW)Worker is internal only, accessible from within Docker network$(NC)"
	@$(DOCKER_COMPOSE) up worker

# View Worker service logs
worker-logs:
	@echo "$(BLUE)Viewing Worker service logs (Ctrl+C to exit)...$(NC)"
	@$(DOCKER_COMPOSE) logs -f worker

# Access Worker container shell
worker-shell:
	@echo "$(GREEN)Accessing Worker container shell...$(NC)"
	@$(DOCKER_COMPOSE) exec worker /bin/bash || $(DOCKER_COMPOSE) run --rm worker /bin/bash

# Run Worker tests only (alias for test-worker)
worker-test: test-worker

# Start Celery Beat scheduler
beat-start:
	@echo "$(GREEN)Starting Celery Beat scheduler...$(NC)"
	@$(DOCKER_COMPOSE) up beat

# View Beat scheduler logs
beat-logs:
	@echo "$(BLUE)Viewing Celery Beat logs (Ctrl+C to exit)...$(NC)"
	@$(DOCKER_COMPOSE) logs -f beat

# Start Flower monitoring dashboard
flower-start:
	@echo "$(GREEN)Starting Flower monitoring dashboard...$(NC)"
	@echo "$(YELLOW)Access Flower at http://localhost/flower/$(NC)"
	@$(DOCKER_COMPOSE) up flower

# View Flower logs
flower-logs:
	@echo "$(BLUE)Viewing Flower logs (Ctrl+C to exit)...$(NC)"
	@$(DOCKER_COMPOSE) logs -f flower

# Check worker status
worker-status:
	@echo "$(BLUE)Checking worker status...$(NC)"
	@$(DOCKER_COMPOSE) ps worker beat flower

# ============================================================================
# Database Management
# ============================================================================

# Access PostgreSQL shell
db-shell:
	@echo "$(GREEN)Accessing PostgreSQL shell...$(NC)"
	@$(DOCKER_COMPOSE) exec postgresql psql -U odin -d odin_db

# Database migration placeholder
db-migrate:
	@echo "$(YELLOW)Database migration not yet implemented$(NC)"
	@echo "$(BLUE)This is a placeholder for future migration commands$(NC)"

# Reset database (WARNING: deletes all data)
db-reset:
	@echo "$(RED)⚠ WARNING: This will delete all data in the database$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW)Resetting database...$(NC)"; \
		$(DOCKER_COMPOSE) exec postgresql psql -U odin -d odin_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"; \
		echo "$(GREEN)✓ Database reset complete!$(NC)"; \
	else \
		echo "$(RED)Cancelled.$(NC)"; \
	fi

# ============================================================================
# Backup & Restore
# ============================================================================

# Backup PostgreSQL database
backup:
	@echo "$(BLUE)Creating database backup...$(NC)"
	@mkdir -p backups
	@$(DOCKER_COMPOSE) exec -T postgresql pg_dump -U odin odin_db > backups/db_backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Backup created in backups/ directory$(NC)"

# Restore PostgreSQL database from backup
restore:
	@echo "$(YELLOW)Available backups:$(NC)"
	@ls -1 backups/*.sql 2>/dev/null || echo "  No backups found"
	@echo ""
	@read -p "Enter backup filename: " backup_file; \
	if [ -f "backups/$$backup_file" ]; then \
		echo "$(YELLOW)Restoring from $$backup_file...$(NC)"; \
		$(DOCKER_COMPOSE) exec -T postgresql psql -U odin odin_db < backups/$$backup_file; \
		echo "$(GREEN)✓ Restore complete!$(NC)"; \
	else \
		echo "$(RED)✗ Backup file not found$(NC)"; \
	fi

# =========================================================================
# Per-API Microservice Testing
# =========================================================================

test-api-confluence:
	@echo "$(BLUE)Running Confluence API tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest -v \
	  tests/unit/api/routes/test_confluence_statistics.py \
	  tests/unit/api/services/test_confluence_service.py \
	  --cov=src/api --cov-report=term-missing --cov-report=xml || true
	@echo "$(GREEN)✓ Confluence API tests complete!$(NC)"

test-api-files:
	@echo "$(BLUE)Running Files API tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest -v \
	  tests/unit/api/routes/test_files.py \
	  --cov=src/api --cov-report=term-missing --cov-report=xml || true
	@echo "$(GREEN)✓ Files API tests complete!$(NC)"

test-api-llm:
	@echo "$(BLUE)Running LLM API tests (LLM-only coverage)...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest -v \
	  tests/unit/api/routes/test_llm.py \
	  tests/unit/api/services/test_llm_analysis_service.py \
	  tests/unit/api/services/test_llm_prompts.py \
	  --cov=src/api/apps/llm_app.py \
	  --cov=src/api/routes/llm.py \
	  --cov=src/api/services/llm_analysis_service.py \
	  --cov=src/api/services/llm_prompts.py \
	  --cov=src/api/services/ollama.py \
	  --cov-report=term-missing --cov-report=xml || true
	@echo "$(GREEN)✓ LLM API tests complete!$(NC)"

test-api-health:
	@echo "$(BLUE)Running Health API tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest -v \
	  tests/unit/api/routes/test_health.py \
	  tests/unit/api/routes/test_health_record.py \
	  tests/unit/api/services/test_db_management.py \
	  tests/unit/api/repositories/test_health_repository.py \
	  --cov=src/api --cov-report=term-missing --cov-report=xml || true
	@echo "$(GREEN)✓ Health API tests complete!$(NC)"

test-api-logs:
	@echo "$(BLUE)Running Logs API tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest -v \
	  tests/unit/api/routes/test_logs.py \
	  tests/unit/api/routes/test_logs_error_paths.py \
	  tests/unit/api/services/test_log_service.py \
	  tests/unit/api/repositories/test_log_repository.py \
	  --cov=src/api --cov-report=term-missing --cov-report=xml || true
	@echo "$(GREEN)✓ Logs API tests complete!$(NC)"

test-api-data:
	@echo "$(BLUE)Running Data API tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest -v \
	  tests/unit/api/routes/test_data.py \
	  tests/unit/api/services/test_database.py \
	  --cov=src/api --cov-report=term-missing --cov-report=xml || true
	@echo "$(GREEN)✓ Data API tests complete!$(NC)"

test-api-secrets:
	@echo "$(BLUE)Running Secrets API tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest -v \
	  tests/unit/api/routes/test_secrets.py \
	  tests/unit/api/services/test_vault.py \
	  --cov=src/api --cov-report=term-missing --cov-report=xml || true
	@echo "$(GREEN)✓ Secrets API tests complete!$(NC)"

test-api-messages:
	@echo "$(BLUE)Running Messages API tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest -v \
	  tests/unit/api/routes/test_messages.py \
	  tests/unit/api/services/test_queue.py \
	  --cov=src/api --cov-report=term-missing --cov-report=xml || true
	@echo "$(GREEN)✓ Messages API tests complete!$(NC)"

test-api-image-analysis:
	@echo "$(BLUE)Running Image Analysis API tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest -v \
	  tests/unit/api/routes/test_image_analysis.py \
	  tests/unit/api/services/test_image_analysis.py \
	  --cov=src/api --cov-report=term-missing --cov-report=xml || true
	@echo "$(GREEN)✓ Image Analysis API tests complete!$(NC)"

# API microservice global test targets

test-api-unit-global:
	@echo "$(BLUE)Running all API unit tests (global)...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/unit/api/ -v -m unit
	@echo "$(GREEN)✓ All API unit tests (global) complete!$(NC)"

test-api-integration-global:
	@echo "$(BLUE)Running all API integration tests (global)...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/integration/api/ -v -m integration
	@echo "$(GREEN)✓ All API integration tests (global) complete!$(NC)"

test-api-regression-global:
	@echo "$(BLUE)Running all API regression tests (global)...$(NC)"
	@$(DOCKER_COMPOSE) run --rm portal pytest tests/regression/ -v -m regression || true
	@echo "$(GREEN)✓ All API regression tests (global) complete!$(NC)"

