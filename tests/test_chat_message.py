from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.database import get_db
from src.routes.chat import get_agent


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
def mock_agent():
    agent = AsyncMock()
    agent.generate_response.return_value = {
        "reply": "Hello! How can I help you?",
        "show_whatsapp_cta": False,
    }
    return agent


async def test_send_message_success(client, app, mock_db_with_business, mock_agent):
    app.dependency_overrides[get_db] = mock_db_with_business

    import src.routes.chat as chat_module
    original = chat_module._agent
    chat_module._agent = mock_agent

    try:
        response = await client.post(
            "/chat/test-biz/message",
            json={"message": "Hi there", "history": []},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "Hello! How can I help you?"
        assert data["show_whatsapp_cta"] is False
        mock_agent.generate_response.assert_called_once()
    finally:
        app.dependency_overrides.clear()
        chat_module._agent = original


async def test_send_message_not_found(client, app):
    async def override():
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result
        yield db

    app.dependency_overrides[get_db] = override
    try:
        response = await client.post(
            "/chat/nonexistent/message",
            json={"message": "Hi", "history": []},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_send_message_trims_history(client, app, mock_db_with_business, mock_agent):
    app.dependency_overrides[get_db] = mock_db_with_business

    import src.routes.chat as chat_module
    original = chat_module._agent
    chat_module._agent = mock_agent

    long_history = [{"role": "user", "content": f"msg{i}"} for i in range(10)]

    try:
        response = await client.post(
            "/chat/test-biz/message",
            json={"message": "Latest", "history": long_history},
        )
        assert response.status_code == 200
        call_args = mock_agent.generate_response.call_args
        assert len(call_args.kwargs["history"]) == 6
    finally:
        app.dependency_overrides.clear()
        chat_module._agent = original


async def test_send_message_with_whatsapp_cta(client, app, mock_db_with_business):
    agent = AsyncMock()
    agent.generate_response.return_value = {
        "reply": "Let me help you book! Here's my WhatsApp.",
        "show_whatsapp_cta": True,
    }

    import src.routes.chat as chat_module
    original = chat_module._agent
    chat_module._agent = agent
    app.dependency_overrides[get_db] = mock_db_with_business

    try:
        response = await client.post(
            "/chat/test-biz/message",
            json={"message": "I want to book", "history": []},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["show_whatsapp_cta"] is True
    finally:
        app.dependency_overrides.clear()
        chat_module._agent = original
