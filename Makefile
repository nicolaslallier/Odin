.PHONY: help setup build rebuild up down restart ps logs shell install clean \
        test test-unit test-integration test-regression test-watch coverage \
        lint format type-check quality check-all \
        services-up services-down services-restart services-logs services-status services-health \
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
CONTAINER_NAME = odin-dev
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
	@echo "  make up              - Start all containers"
	@echo "  make down            - Stop all containers"
	@echo "  make restart         - Restart all containers"
	@echo "  make ps              - Show running containers"
	@echo "  make logs            - View logs from all containers"
	@echo "  make shell           - Access app container shell"
	@echo ""
	@echo "$(GREEN)🧪 Testing:$(NC)"
	@echo "  make test            - Run all tests"
	@echo "  make test-unit       - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-regression - Run regression tests only"
	@echo "  make test-watch      - Run tests in watch mode"
	@echo "  make coverage        - Generate coverage report (HTML + terminal)"
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
	@echo "$(YELLOW)💡 Tip: Run 'make services-up' to start all infrastructure services$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"

# ============================================================================
# Setup & Build
# ============================================================================

# Initial project setup
setup: build init-env
	@echo "$(GREEN)✓ Setting up development environment...$(NC)"
	@$(DOCKER_COMPOSE) run --rm app pip install -r requirements-dev.txt
	@echo "$(GREEN)✓ Setup complete!$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Edit .env with your configuration"
	@echo "  2. Run 'make services-up' to start services"
	@echo "  3. Run 'make init-services' to initialize services"

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

# Start all containers
up:
	@echo "$(GREEN)Starting all containers...$(NC)"
	@$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✓ Containers started!$(NC)"
	@echo "$(YELLOW)Use 'make ps' to see running containers$(NC)"
	@echo "$(YELLOW)Use 'make shell' to access the app container$(NC)"

# Stop all containers
down:
	@echo "$(YELLOW)Stopping all containers...$(NC)"
	@$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Containers stopped!$(NC)"

# Restart all containers
restart:
	@echo "$(YELLOW)Restarting all containers...$(NC)"
	@$(DOCKER_COMPOSE) restart
	@echo "$(GREEN)✓ Containers restarted!$(NC)"

# Show running containers
ps:
	@echo "$(BLUE)Running containers:$(NC)"
	@$(DOCKER_COMPOSE) ps

# View logs
logs:
	@echo "$(BLUE)Viewing logs (Ctrl+C to exit)...$(NC)"
	@$(DOCKER_COMPOSE) logs -f

# Access app container shell
shell:
	@echo "$(GREEN)Accessing app container shell...$(NC)"
	@$(DOCKER_COMPOSE) exec app /bin/bash || $(DOCKER_COMPOSE) run --rm app /bin/bash

# ============================================================================
# Testing
# ============================================================================

# Run all tests
test:
	@echo "$(BLUE)Running all tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm app pytest tests/ -v
	@echo "$(GREEN)✓ Tests complete!$(NC)"

# Run unit tests only
test-unit:
	@echo "$(BLUE)Running unit tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm app pytest tests/unit/ -v -m unit
	@echo "$(GREEN)✓ Unit tests complete!$(NC)"

# Run integration tests only
test-integration:
	@echo "$(BLUE)Running integration tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm app pytest tests/integration/ -v -m integration
	@echo "$(GREEN)✓ Integration tests complete!$(NC)"

# Run regression tests
test-regression:
	@echo "$(BLUE)Running regression tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm app pytest tests/regression/ -v -m regression
	@echo "$(GREEN)✓ Regression tests complete!$(NC)"

# Run tests in watch mode
test-watch:
	@echo "$(BLUE)Running tests in watch mode (Ctrl+C to exit)...$(NC)"
	@$(DOCKER_COMPOSE) run --rm app pytest-watch tests/ -v

# Generate coverage report
coverage:
	@echo "$(BLUE)Generating coverage report...$(NC)"
	@$(DOCKER_COMPOSE) run --rm app pytest tests/ --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "$(GREEN)✓ Coverage report generated!$(NC)"
	@echo "$(YELLOW)HTML report: htmlcov/index.html$(NC)"

# ============================================================================
# Code Quality
# ============================================================================

# Run linting
lint:
	@echo "$(BLUE)Running linter (ruff)...$(NC)"
	@$(DOCKER_COMPOSE) run --rm app ruff check src/ tests/
	@echo "$(GREEN)✓ Linting complete!$(NC)"

# Format code
format:
	@echo "$(BLUE)Formatting code with black...$(NC)"
	@$(DOCKER_COMPOSE) run --rm app black src/ tests/
	@echo "$(GREEN)✓ Formatting complete!$(NC)"

# Type checking
type-check:
	@echo "$(BLUE)Running type checker (mypy)...$(NC)"
	@$(DOCKER_COMPOSE) run --rm app mypy src/
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
	@$(DOCKER_COMPOSE) run --rm app pip install -e .
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

