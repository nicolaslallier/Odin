# Odin Web Interface - Quick Start Guide

## Version 0.2.0

This guide helps you get started with the newly implemented FastAPI web interface.

## Overview

The Odin web interface is a modern, FastAPI-based web application featuring:
- **Hello World** landing page with beautiful, responsive design
- **TDD Development** - Built with Test-Driven Development (100% coverage)
- **SOLID Principles** - Clean architecture following all SOLID principles
- **Production Ready** - Integrated with nginx reverse proxy

## Quick Start

### 1. Build and Start Services

```bash
# Rebuild with new dependencies
make rebuild

# Start all infrastructure services
make services-up
```

### 2. Run the Web Application

**Option A: Development Mode (with auto-reload)**
```bash
make web-dev
```

**Option B: Inside Container**
```bash
make shell
python -m src.web
```

### 3. Access the Application

- **Direct Access**: http://localhost:8000/
- **Via Nginx Proxy**: http://localhost/app/
- **Health Check**: http://localhost:8000/health

## Available Commands

### Web-Specific Commands
```bash
make web-dev      # Start web server in development mode
make web-logs     # View web application logs
make web-shell    # Access web container shell
make web-test     # Run web application tests only
```

### Testing Commands
```bash
make test         # Run all tests (including web tests)
make coverage     # Generate coverage report (should be 100%)
make web-test     # Run only web application tests
```

## Project Structure

```
src/web/
├── __init__.py          # Package initialization
├── __main__.py          # Entry point for running the app
├── app.py               # FastAPI application factory
├── config.py            # Configuration management (Pydantic)
├── routes/
│   ├── __init__.py
│   └── home.py          # Home page route handlers
├── templates/
│   ├── base.html        # Base template with layout
│   └── index.html       # Hello World landing page
└── static/
    └── css/
        └── style.css    # Modern CSS styling

tests/
├── unit/web/            # Unit tests (isolated components)
│   ├── test_config.py
│   ├── test_app_factory.py
│   └── test_home_routes.py
└── integration/web/     # Integration tests (full app)
    ├── test_web_app.py
    └── test_template_rendering.py
```

## Configuration

Configure the web application via environment variables in `.env`:

```bash
WEB_HOST=0.0.0.0          # Host to bind to
WEB_PORT=8000             # Port to listen on
WEB_RELOAD=true           # Enable auto-reload (development)
WEB_LOG_LEVEL=info        # Logging level (debug, info, warning, error, critical)
```

## Development Workflow

### TDD Approach (Followed During Development)

1. **RED**: Write failing tests first
2. **GREEN**: Write minimal code to pass tests
3. **REFACTOR**: Improve code while keeping tests green

### Adding New Features

1. Write tests in `tests/unit/web/` or `tests/integration/web/`
2. Run tests to ensure they fail: `make web-test`
3. Implement the feature
4. Run tests to ensure they pass: `make web-test`
5. Check coverage: `make coverage` (should maintain 100%)
6. Refactor if needed

### Adding New Routes

1. Create route tests in `tests/unit/web/test_<feature>_routes.py`
2. Implement routes in `src/web/routes/<feature>.py`
3. Register router in `src/web/app.py`
4. Create templates in `src/web/templates/`
5. Verify tests pass and coverage is maintained

## Architecture

### SOLID Principles Applied

- **Single Responsibility**: Each module has one clear purpose
  - `config.py` - Configuration only
  - `app.py` - Application factory only
  - `routes/home.py` - Home page routes only

- **Open/Closed**: Extensible via router system
  - New routes can be added without modifying existing code
  - Router registration pattern allows easy extension

- **Liskov Substitution**: Proper type hierarchies
  - All components follow their contracts
  - Subtypes can replace base types safely

- **Interface Segregation**: Focused interfaces
  - Small, specific route modules
  - No unnecessary dependencies

- **Dependency Inversion**: FastAPI dependency injection
  - Configuration injected via dependencies
  - Easy to mock and test

### Key Design Patterns

1. **Factory Pattern**: `create_app()` function
2. **Dependency Injection**: FastAPI's `Depends()`
3. **Template Method**: Jinja2 template inheritance
4. **Configuration Pattern**: Environment-based config

## Testing

### Running Tests

```bash
# All tests
make test

# Only web tests
make web-test

# With coverage report
make coverage

# Watch mode (runs on file changes)
make test-watch
```

### Test Coverage

All code has 100% test coverage:
- Unit tests: Configuration, app factory, route handlers
- Integration tests: Full application, template rendering
- Edge cases: Error handling, validation, boundaries

### Writing Tests

Example test structure:

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.unit
class TestMyFeature:
    @pytest.fixture
    def client(self) -> TestClient:
        from src.web.app import create_app
        return TestClient(create_app())
    
    def test_my_feature(self, client: TestClient) -> None:
        response = client.get("/my-route")
        assert response.status_code == 200
```

## Troubleshooting

### Web Server Won't Start

```bash
# Check if port 8000 is already in use
lsof -i :8000

# Check logs
make web-logs

# Restart services
make down
make up
```

### Tests Failing

```bash
# Run with verbose output
make web-test

# Check specific test file
docker-compose run --rm app pytest tests/unit/web/test_config.py -v

# Check coverage
make coverage
```

### Nginx Proxy Not Working

```bash
# Check nginx is running
docker ps | grep nginx

# Check nginx logs
docker logs odin-nginx

# Restart nginx
docker-compose restart nginx
```

## Next Steps

### Suggested Enhancements

1. **Add More Pages**
   - About page
   - Documentation page
   - API documentation (FastAPI auto-generates this!)

2. **Add API Endpoints**
   - RESTful API for data access
   - Authentication endpoints
   - Health checks with detailed metrics

3. **Database Integration**
   - Connect to PostgreSQL
   - Create models and migrations
   - Add data persistence

4. **User Authentication**
   - Login/logout functionality
   - Session management
   - Role-based access control

5. **Advanced Features**
   - WebSocket support for real-time updates
   - File upload handling
   - Form validation
   - AJAX interactions

## Resources

- FastAPI Documentation: https://fastapi.tiangolo.com/
- Jinja2 Documentation: https://jinja.palletsprojects.com/
- Pydantic Documentation: https://docs.pydantic.dev/
- pytest Documentation: https://docs.pytest.org/

## Support

For issues or questions:
1. Check the logs: `make web-logs`
2. Review test output: `make web-test`
3. Check Docker status: `make ps`
4. Review this guide and README.md

---

**Happy Coding!** 🚀

