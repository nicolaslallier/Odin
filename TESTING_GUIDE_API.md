# API Testing Guide: 100% Coverage & Real Integration Tests

This guide documents the complete testing setup for achieving **0 errors, 0 warnings, 0 skips, and 100% code coverage** for the Odin API tests.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Test Infrastructure](#test-infrastructure)
- [Running Tests](#running-tests)
- [Coverage Requirements](#coverage-requirements)
- [Integration Testing](#integration-testing)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Services
All tests require the following services to be running:

- **PostgreSQL**: Database for data persistence
- **MinIO**: Object storage for file management
- **RabbitMQ**: Message queue for async operations
- **Vault**: Secrets management
- **Ollama**: LLM service for AI operations

### Starting Services

```bash
# Start all required services
make services-up

# Or using docker-compose directly
docker-compose up -d postgresql minio rabbitmq vault ollama

# Verify services are healthy
make services-health
```

## Test Infrastructure

### Test Organization

```
tests/
├── unit/api/                 # Unit tests with mocked dependencies
│   ├── routes/              # Route handler tests
│   ├── services/            # Service layer tests
│   ├── repositories/        # Repository tests
│   └── test_*.py           # Other unit tests
├── integration/api/         # Integration tests with real services
│   ├── test_api_integration.py
│   └── test_image_analysis_flow.py
└── conftest.py             # Shared fixtures
```

### Test Types

1. **Unit Tests** (`tests/unit/api/`):
   - Mocked external dependencies
   - Fast execution
   - Test individual components in isolation

2. **Integration Tests** (`tests/integration/api/`):
   - Real service dependencies
   - End-to-end workflows
   - Verify component interactions

## Running Tests

### Using Makefile (Recommended)

```bash
# Run all API tests with coverage (unit + integration)
make test-api

# Run only unit tests
make test-api-unit

# Run only integration tests
make test-api-integration

# Generate coverage report
make coverage-api
```

### Using Docker Compose Directly

```bash
# Run all tests with 100% coverage requirement
docker-compose exec api bash -c "cd /app && pytest tests/unit/api/ tests/integration/api/ -v \
    --cov=src/api --cov-report=term-missing --cov-report=xml --cov-fail-under=100"
```

### Using pytest Directly (Inside Container)

```bash
# Enter API container
docker-compose exec api bash

# Run tests
cd /app
pytest tests/unit/api/ tests/integration/api/ -v \
    --cov=src/api \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=xml \
    --cov-fail-under=100
```

## Coverage Requirements

### Configuration

Coverage is configured in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/worker/*",     # Worker is tested separately
    "*/web/*",        # Web is tested separately
]

[tool.coverage.report]
fail_under = 100.0  # Strict 100% requirement for API
show_missing = true
precision = 2
```

### Coverage Targets

- **API Code**: 100% line and branch coverage
- **Excluded**: Worker, Web, and Test files
- **Enforcement**: Tests fail if coverage drops below 100%

### Viewing Coverage Reports

```bash
# Generate HTML coverage report
pytest tests/unit/api/ tests/integration/api/ --cov=src/api --cov-report=html

# Open in browser
open htmlcov/index.html
```

## Integration Testing

### Environment Configuration

Integration tests use environment variables for service connections:

```bash
# Default values (defined in docker-compose.yml)
POSTGRES_DSN=postgresql://odin:odin_dev_password@postgresql:5432/odin_db
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
RABBITMQ_URL=amqp://odin:odin_dev_password@rabbitmq:5672//
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=dev-root-token
OLLAMA_BASE_URL=http://ollama:11434
```

### Test Fixtures

Integration test fixtures are defined in `tests/integration/api/test_image_analysis_flow.py`:

```python
@pytest.fixture
def test_config(self) -> APIConfig:
    """Create test configuration using environment variables."""
    return APIConfig(
        host="0.0.0.0",
        port=8001,
        postgres_dsn=os.getenv("POSTGRES_DSN", "..."),
        # ... other config
    )

@pytest.fixture
def client(self, test_config: APIConfig) -> TestClient:
    """Create test client with real services."""
    app = create_app(config=test_config)
    return TestClient(app)
```

### Test Patterns

1. **Service Health Checks**:
   ```python
   def test_service_availability(self, client: TestClient) -> None:
       response = client.get("/health")
       assert response.status_code == 200
   ```

2. **End-to-End Workflows**:
   ```python
   def test_full_workflow(self, client: TestClient) -> None:
       # Step 1: Create resource
       # Step 2: Retrieve resource
       # Step 3: Update resource
       # Step 4: Delete resource
       # Step 5: Verify deletion
   ```

## Quality Checks

### Linting

```bash
# Run ruff linter
make lint

# Or with docker-compose
docker-compose run --rm portal ruff check src/ tests/
```

### Formatting

```bash
# Format code with black
make format

# Or with docker-compose
docker-compose run --rm portal black src/ tests/
```

### Type Checking

```bash
# Run mypy type checker
make type-check

# Or with docker-compose
docker-compose run --rm portal mypy src/api/
```

## Test Markers

Tests use pytest markers for categorization:

```python
@pytest.mark.unit          # Unit test (mocked dependencies)
@pytest.mark.integration   # Integration test (real services)
@pytest.mark.asyncio       # Async test
```

### Running by Marker

```bash
# Run only unit tests
pytest -v -m unit tests/unit/api/

# Run only integration tests
pytest -v -m integration tests/integration/api/

# Run only async tests
pytest -v -m asyncio tests/unit/api/
```

## Troubleshooting

### Issue: Tests Fail with Service Unavailable

**Solution**: Ensure all services are running and healthy

```bash
# Check service status
docker-compose ps

# Check service health
make services-health

# Restart services if needed
make services-restart
```

### Issue: Coverage Below 100%

**Solution**: Check coverage report for missing lines

```bash
# Generate detailed coverage report
pytest tests/unit/api/ tests/integration/api/ \
    --cov=src/api \
    --cov-report=term-missing

# Or view HTML report
pytest tests/unit/api/ tests/integration/api/ \
    --cov=src/api \
    --cov-report=html
open htmlcov/index.html
```

### Issue: Test Warnings

**Solution**: Tests are configured to treat warnings as errors

```toml
# In pyproject.toml
filterwarnings = [
    "error",
    "ignore::DeprecationWarning:passlib.*",
    "ignore::DeprecationWarning:pkg_resources.*",
]
```

To fix warnings:
1. Identify the warning source
2. Either fix the code or add to filterwarnings
3. Re-run tests

### Issue: Skipped Tests

**Solution**: All skips have been removed. If you see skips:

1. Check for `@pytest.mark.skip` decorators
2. Check for `pytest.skip()` calls in test bodies
3. Remove or implement the skipped tests

## CI/CD Integration

### Docker-Based CI

```yaml
# Example GitHub Actions workflow
name: API Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start services
        run: docker-compose up -d postgresql minio rabbitmq vault ollama
      
      - name: Wait for services
        run: |
          docker-compose exec -T postgresql pg_isready -U odin
          # ... wait for other services
      
      - name: Run tests
        run: make test-api
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## Best Practices

### Writing New Tests

1. **Start with TDD**: Write test first, then implementation
2. **Test Isolation**: Each test should be independent
3. **Descriptive Names**: Use clear test names that describe behavior
4. **Arrange-Act-Assert**: Follow AAA pattern
5. **Mock Appropriately**: Mock external dependencies in unit tests
6. **Real Services**: Use real services in integration tests

### Maintaining 100% Coverage

1. **Cover Error Paths**: Test both success and failure cases
2. **Edge Cases**: Test boundary conditions
3. **Exception Handling**: Test all exception scenarios
4. **Async Code**: Test async functions with `pytest-asyncio`
5. **Type Hints**: Use type hints everywhere

### Performance Considerations

- Unit tests should be fast (< 1s per test)
- Integration tests may be slower (allow up to 10s)
- Use fixtures to share expensive setup
- Consider parallel test execution with pytest-xdist

## Summary

This guide provides a complete testing strategy for the Odin API service, ensuring:

- ✅ **0 Errors**: All tests pass
- ✅ **0 Warnings**: No warnings emitted
- ✅ **0 Skips**: All tests are executed
- ✅ **100% Coverage**: Complete code coverage for API

The test infrastructure is:
- **Docker-friendly**: All tests run in containers
- **Stateless**: No persistent state between runs
- **Reproducible**: Consistent results across environments
- **Maintainable**: Clear structure and documentation

For questions or issues, refer to the main project documentation or open an issue.

