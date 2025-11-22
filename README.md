# Odin

A Python project following Test-Driven Development (TDD), SOLID principles, and industry best practices with comprehensive testing and Docker containerization.

## Overview

Odin is a Python development environment configured for senior-level development practices, emphasizing:

- **Test-Driven Development (TDD)**: Write tests first, then implement
- **SOLID Principles**: Clean, maintainable, and extensible code architecture
- **100% Test Coverage**: Mandatory coverage for unit, integration, and regression tests
- **Docker Containerization**: Consistent development and deployment environments
- **Code Quality**: Automated linting, formatting, and type checking

## Features

- Python 3.12 development environment
- Comprehensive testing framework (pytest with coverage)
- Docker-based development workflow
- Makefile automation for common tasks
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

2. Build and start the development environment:
```bash
make setup
make up
```

3. Access the container shell:
```bash
make shell
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
├── .cursorrules      # Cursor AI development rules
├── Dockerfile        # Docker container definition
├── docker-compose.yml # Docker Compose configuration
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

## Docker Usage

### Development Container

The development container includes:
- Python 3.12
- All development dependencies
- Pre-configured environment

### Docker Commands

```bash
# Build the image
make build

# Start containers
make up

# Stop containers
make down

# Access container shell
make shell
```

### Volume Mounts

The project directory is mounted as a volume, allowing live code editing without rebuilding the container.

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
