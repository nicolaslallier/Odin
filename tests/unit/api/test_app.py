import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace
from fastapi import FastAPI

from src.api.app import create_app, get_container
from src.api.exceptions import ResourceNotFoundError

class DummyConfig:
    log_level = "INFO"
    postgres_dsn = "dsn"
    host = "0.0.0.0"
    port = 8001

@pytest.fixture
def app_with_container():
    app = create_app(DummyConfig())
    # Add dummy ServiceContainer to state
    app.state.container = "container-mock"
    return app

@pytest.fixture
def app_without_container():
    app = create_app(DummyConfig())
    # No .container in state
    return app

@pytest.mark.asyncio
async def test_not_found_handler_returns_404():
    app = create_app(DummyConfig())
    handler = None
    # find the dynamically registered handler
    for k, v in app.exception_handlers.items():
        if k == ResourceNotFoundError:
            handler = v
    req = MagicMock()
    exc = ResourceNotFoundError("not here")
    response = await handler(req, exc)
    assert response.status_code == 404
    assert response.body is not None
    assert b"not here" in response.body


def test_get_container_happy(app_with_container):
    container = get_container(app_with_container)
    assert container == "container-mock"

def test_get_container_error(app_without_container):
    # Should raise if no container
    with pytest.raises(RuntimeError, match="Service container not initialized"):
        get_container(app_without_container)
