# Makefile Testing Guide

This guide explains how to test the Odin project components using the Makefile.

## Test All Components

Run tests across all components (API, Web, Worker):

```bash
make test              # Run all tests (unit + integration + regression)
make test-unit         # Run all unit tests
make test-integration  # Run all integration tests
make test-regression   # Run regression tests only
make coverage          # Generate coverage report for all components
```

## Component-Specific Testing

### API Component

```bash
make test-api              # Run all API tests (unit + integration)
make test-api-unit         # Run API unit tests only
make test-api-integration  # Run API integration tests only
make coverage-api          # Generate API-specific coverage report
```

Alternative alias:
```bash
make api-test             # Same as test-api
```

### Web Component

```bash
make test-web              # Run all Web tests (unit + integration)
make test-web-unit         # Run Web unit tests only
make test-web-integration  # Run Web integration tests only
make coverage-web          # Generate Web-specific coverage report
```

Alternative alias:
```bash
make web-test             # Same as test-web
```

### Worker Component

```bash
make test-worker              # Run all Worker tests (unit + integration)
make test-worker-unit         # Run Worker unit tests only
make test-worker-integration  # Run Worker integration tests only
make coverage-worker          # Generate Worker-specific coverage report
```

Alternative alias:
```bash
make worker-test             # Same as test-worker
```

## Other Testing Utilities

```bash
make test-services     # Run service accessibility tests
make test-watch        # Run tests in watch mode (auto-rerun on changes)
make check-services    # Check which services are accessible (diagnostic)
```

## Component Development & Debugging

### API Service
```bash
make api-dev          # Start API server in development mode
make api-logs         # View API service logs
make api-shell        # Access API container shell
make api-health       # Check API health
```

### Web Service
```bash
make web-dev          # Start web server in development mode
make web-logs         # View web application logs
make web-shell        # Access web container shell
```

### Worker Service
```bash
make worker-dev       # Start Worker in development mode
make worker-logs      # View Worker service logs
make worker-shell     # Access Worker container shell
```

## Examples

### Test only the API component's unit tests
```bash
make test-api-unit
```

### Test only the Web component with coverage
```bash
make coverage-web
```

### Run all Worker tests
```bash
make test-worker
```

### Quick check: Run unit tests for all components
```bash
make test-unit
```

## Notes

- All tests run inside Docker containers via `docker-compose`
- Component-specific tests only run tests for that specific component
- Coverage reports are generated in `htmlcov/` directory and also displayed in terminal
- Test markers (`-m unit`, `-m integration`, `-m regression`) are used to filter tests
