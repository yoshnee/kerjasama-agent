from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.database import get_db


@pytest.fixture
def mock_db_with_business(sample_business):
    async def override_get_db():
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_business
        db.execute.return_value = result
        yield db

    return override_get_db


@pytest.fixture
def mock_db_not_found():
    async def override_get_db():
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result
        yield db

    return override_get_db


async def test_get_info_success(client, app, mock_db_with_business):
    app.dependency_overrides[get_db] = mock_db_with_business
    try:
        response = await client.get("/chat/test-biz/info")
        assert response.status_code == 200
        data = response.json()
        assert data["business_name"] == "Alice Photography"
        assert data["avatar_initial"] == "A"
        assert data["whatsapp_number"] == "60123456789"
        assert data["accent_color"] == "#E2A9F1"
        assert data["has_services"] is True
        assert data["services"] == ["Portrait", "Wedding", "Event"]
    finally:
        app.dependency_overrides.clear()


async def test_get_info_not_found(client, app, mock_db_not_found):
    app.dependency_overrides[get_db] = mock_db_not_found
    try:
        response = await client.get("/chat/nonexistent/info")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_get_info_no_services(client, app, sample_business):
    sample_business.services = None

    async def override():
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_business
        db.execute.return_value = result
        yield db

    app.dependency_overrides[get_db] = override
    try:
        response = await client.get("/chat/test-biz/info")
        assert response.status_code == 200
        data = response.json()
        assert data["has_services"] is False
        assert data["services"] is None
    finally:
        app.dependency_overrides.clear()


async def test_avatar_initial_fallback(client, app, sample_business):
    sample_business.owner_name = None
    sample_business.business_name = "Zen Studio"

    async def override():
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = sample_business
        db.execute.return_value = result
        yield db

    app.dependency_overrides[get_db] = override
    try:
        response = await client.get("/chat/test-biz/info")
        assert response.status_code == 200
        assert response.json()["avatar_initial"] == "Z"
    finally:
        app.dependency_overrides.clear()
