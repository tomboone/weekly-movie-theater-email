from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

TEST_API_KEY = "test-secret-key"


def make_mock_settings() -> MagicMock:
    mock = MagicMock()
    mock.trigger_api_key = TEST_API_KEY
    mock.schedule_cron = "0 10 * * 5"
    mock.schedule_timezone = "America/New_York"
    mock.movie_state_path = "/tmp/nonexistent.json"
    return mock


@pytest.fixture()
async def async_client():
    """Async HTTPX client wrapping the FastAPI app with mocked dependencies."""
    with (
        patch("server.run_pipeline", new_callable=AsyncMock) as mock_pipeline,
        patch("server._should_run_on_startup", return_value=False),
        patch("server.settings", make_mock_settings()),
    ):
        from server import app

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, mock_pipeline


async def test_health_returns_ok(async_client):
    """GET /health returns 200 with {status: ok}."""
    client, _ = async_client
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_trigger_with_valid_auth(async_client):
    """POST /trigger with correct Bearer token returns 200 with {status: success}."""
    client, mock_pipeline = async_client
    response = await client.post(
        "/trigger",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    mock_pipeline.assert_called_once()


async def test_trigger_without_auth(async_client):
    """POST /trigger with no auth returns 401."""
    client, _ = async_client
    response = await client.post("/trigger")
    assert response.status_code == 401


async def test_trigger_with_bad_auth(async_client):
    """POST /trigger with wrong Bearer token returns 401."""
    client, _ = async_client
    response = await client.post(
        "/trigger",
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401


async def test_trigger_with_date_override(async_client):
    """POST /trigger?date=03-27-2026 calls run_pipeline with the date override."""
    client, mock_pipeline = async_client
    response = await client.post(
        "/trigger",
        params={"date": "03-27-2026"},
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

    call_kwargs = mock_pipeline.call_args
    assert call_kwargs.kwargs.get("date_override") == "03-27-2026"
