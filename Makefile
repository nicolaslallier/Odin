.PHONY: help setup build up down test test-unit test-integration test-regression coverage lint format clean shell install

# Variables
DOCKER_COMPOSE = docker-compose
DOCKER = docker
PYTHON = python
CONTAINER_NAME = odin-dev

# Default target
help:
	@echo "Available targets:"
	@echo "  make setup          - Initial project setup (install dependencies)"
	@echo "  make build          - Build Docker image"
	@echo "  make up             - Start Docker containers"
	@echo "  make down           - Stop Docker containers"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-regression - Run regression tests"
	@echo "  make coverage       - Generate coverage report"
	@echo "  make lint           - Run linting (ruff)"
	@echo "  make format         - Format code (black)"
	@echo "  make type-check     - Run type checking (mypy)"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make shell          - Access container shell"
	@echo "  make install        - Install package in development mode"

# Initial project setup
setup: build
	@echo "Setting up development environment..."
	$(DOCKER_COMPOSE) run --rm app pip install -r requirements-dev.txt
	@echo "Setup complete!"

# Build Docker image
build:
	@echo "Building Docker image..."
	$(DOCKER_COMPOSE) build

# Start Docker containers
up:
	@echo "Starting Docker containers..."
	$(DOCKER_COMPOSE) up -d
	@echo "Containers started. Use 'make shell' to access the container."

# Stop Docker containers
down:
	@echo "Stopping Docker containers..."
	$(DOCKER_COMPOSE) down

# Run all tests
test:
	@echo "Running all tests..."
	$(DOCKER_COMPOSE) run --rm app pytest tests/ -v

# Run unit tests only
test-unit:
	@echo "Running unit tests..."
	$(DOCKER_COMPOSE) run --rm app pytest tests/unit/ -v -m unit

# Run integration tests only
test-integration:
	@echo "Running integration tests..."
	$(DOCKER_COMPOSE) run --rm app pytest tests/integration/ -v -m integration

# Run regression tests
test-regression:
	@echo "Running regression tests..."
	$(DOCKER_COMPOSE) run --rm app pytest tests/regression/ -v -m regression

# Generate coverage report
coverage:
	@echo "Generating coverage report..."
	$(DOCKER_COMPOSE) run --rm app pytest tests/ --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "Coverage report generated in htmlcov/index.html"

# Run linting
lint:
	@echo "Running linter (ruff)..."
	$(DOCKER_COMPOSE) run --rm app ruff check src/ tests/
	@echo "Linting complete!"

# Format code
format:
	@echo "Formatting code with black..."
	$(DOCKER_COMPOSE) run --rm app black src/ tests/
	@echo "Formatting complete!"

# Type checking
type-check:
	@echo "Running type checker (mypy)..."
	$(DOCKER_COMPOSE) run --rm app mypy src/
	@echo "Type checking complete!"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -r {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/ coverage.xml .tox/ .nox/
	@echo "Clean complete!"

# Access container shell
shell:
	@echo "Accessing container shell..."
	$(DOCKER_COMPOSE) exec app /bin/bash || $(DOCKER_COMPOSE) run --rm app /bin/bash

# Install package in development mode
install:
	@echo "Installing package in development mode..."
	$(DOCKER_COMPOSE) run --rm app pip install -e .

# Quality check (runs all quality checks)
quality: lint type-check format
	@echo "All quality checks complete!"

# Full test suite with coverage
test-full: coverage lint type-check
	@echo "Full test suite complete!"

