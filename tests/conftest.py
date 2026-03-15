import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from src.models import Business, OAuthToken


@pytest.fixture
def sample_business():
    biz = MagicMock(spec=Business)
    biz.id = uuid.uuid4()
    biz.user_id = uuid.uuid4()
    biz.slug = "test-biz"
    biz.owner_name = "Alice"
    biz.business_name = "Alice Photography"
    biz.business_type = "Photography"
    biz.location = "Kuala Lumpur"
    biz.whatsapp_number = "60123456789"
    biz.about = "Professional photography services"
    biz.pricing_text = "Starting from RM500"
    biz.services = ["Portrait", "Wedding", "Event"]
    biz.accent_color = "#E2A9F1"
    biz.is_active = True
    return biz


@pytest.fixture
def sample_oauth_token(sample_business):
    token = MagicMock(spec=OAuthToken)
    token.id = uuid.uuid4()
    token.user_id = sample_business.user_id
    token.access_token = "encrypted_access"
    token.refresh_token = "encrypted_refresh"
    token.expires_at = None
    return token


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.fixture
def app():
    from main import app
    return app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
