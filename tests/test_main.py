import pytest


async def test_health_check(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


async def test_cors_headers(client):
    response = await client.options(
        "/chat/test/info",
        headers={
            "Origin": "https://chat.kerjasama.dev",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "https://chat.kerjasama.dev"


async def test_cors_rejected(client):
    response = await client.options(
        "/chat/test/info",
        headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers
