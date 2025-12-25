"""Shared pytest fixtures for all test modules."""

import pytest


@pytest.fixture(scope="session")
def test_config() -> dict:
    """
    Provide test configuration shared across all test sessions.

    Returns configuration values used across multiple test files.
    """
    return {
        "test_timeout": 30,
        "mock_whatsapp_token": "test_verify_token",
        "mock_database_url": "postgresql://test:test@localhost:5432/test_db",
    }
