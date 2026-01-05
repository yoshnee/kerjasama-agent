"""Tests for main application module."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked services."""
    # Mock init_services to avoid loading the classifier during tests
    with patch("src.webhook.init_services"):
        from main import app
        yield TestClient(app, raise_server_exceptions=False)


def test_health_check(client):
    """
    Test the health check endpoint.

    Should verify:
    - GET / returns 200 status code
    - Response body contains {"status": "healthy"}
    """
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_app_startup():
    """
    Test the application startup.

    Should verify:
    - FastAPI app initializes without errors
    - App title and version are correctly set
    """
    with patch("src.webhook.init_services"):
        from main import app

        assert app.title == "Kerjasama Agent"
        assert app.version == "0.1.0"
