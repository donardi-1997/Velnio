from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient

from app.core.config import settings


async def _register(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Test12345!",
            "first_name": "Meta",
            "last_name": "Tester",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_meta_ads_status_not_connected(client: AsyncClient):
    token = await _register(client, "meta-status@test.com")
    response = await client.get("/api/meta-ads/status", headers=_headers(token))
    assert response.status_code == 200
    assert response.json() == {
        "connected": False,
        "expired": False,
        "mode": "mock",
        "meta_user_id": None,
        "meta_user_name": None,
        "connected_at": None,
        "expires_at": None,
    }


@pytest.mark.asyncio
async def test_meta_ads_mock_connection_lists_accounts(client: AsyncClient):
    token = await _register(client, "meta-connect@test.com")
    headers = _headers(token)

    connect = await client.post("/api/meta-ads/connect-mock", headers=headers)
    assert connect.status_code == 200
    assert connect.json()["connected"] is True

    status = await client.get("/api/meta-ads/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["connected"] is True
    assert status.json()["expired"] is False
    assert status.json()["mode"] == "mock"
    assert status.json()["meta_user_id"] == "100000000000001"

    accounts = await client.get("/api/meta-ads/ad-accounts", headers=headers)
    assert accounts.status_code == 200
    payload = accounts.json()
    assert len(payload) == 2
    assert payload[0]["id"].startswith("act_")
    assert payload[0]["currency"] == "USD"


@pytest.mark.asyncio
async def test_meta_ads_delivery_resources_are_discovered_read_only(client: AsyncClient):
    token = await _register(client, "meta-resources@test.com")
    headers = _headers(token)
    await client.post("/api/meta-ads/connect-mock", headers=headers)

    response = await client.get(
        "/api/meta-ads/ad-accounts/act_1000000001/delivery-resources",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ad_account_id"] == "act_1000000001"
    assert len(payload["pixels"]) == 1
    assert payload["pixels"][0]["id"].isdigit()
    assert payload["pixels"][0]["name"] == "Velnio Demo Pixel"
    assert len(payload["pages"]) == 1
    assert payload["pages"][0]["name"] == "Velnio Demo Page"
    assert len(payload["instagram_accounts"]) == 1
    assert payload["instagram_accounts"][0]["username"] == "velnio_demo"


@pytest.mark.asyncio
async def test_meta_ads_delivery_resources_require_connection(client: AsyncClient):
    token = await _register(client, "meta-resources-no-connection@test.com")
    response = await client.get(
        "/api/meta-ads/ad-accounts/act_1000000001/delivery-resources",
        headers=_headers(token),
    )
    assert response.status_code == 400
    assert "not connected" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ads_delivery_resources_reject_inaccessible_account(client: AsyncClient):
    token = await _register(client, "meta-resources-inaccessible@test.com")
    headers = _headers(token)
    await client.post("/api/meta-ads/connect-mock", headers=headers)

    response = await client.get(
        "/api/meta-ads/ad-accounts/act_9999999999/delivery-resources",
        headers=headers,
    )
    assert response.status_code == 403
    assert "not accessible" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ads_delivery_resources_reject_malformed_account(client: AsyncClient):
    token = await _register(client, "meta-resources-malformed@test.com")
    headers = _headers(token)
    await client.post("/api/meta-ads/connect-mock", headers=headers)

    response = await client.get(
        "/api/meta-ads/ad-accounts/not-an-account/delivery-resources",
        headers=headers,
    )
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ads_disconnect_revokes_local_connection(client: AsyncClient):
    token = await _register(client, "meta-disconnect@test.com")
    headers = _headers(token)
    await client.post("/api/meta-ads/connect-mock", headers=headers)

    disconnect = await client.post("/api/meta-ads/disconnect", headers=headers)
    assert disconnect.status_code == 200
    assert disconnect.json()["disconnected"] is True

    status = await client.get("/api/meta-ads/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["connected"] is False

    accounts = await client.get("/api/meta-ads/ad-accounts", headers=headers)
    assert accounts.status_code == 400
    assert "not connected" in accounts.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ads_oauth_state_is_single_use(client: AsyncClient):
    token = await _register(client, "meta-state@test.com")
    headers = _headers(token)

    start = await client.get("/api/meta-ads/connect", headers=headers)
    assert start.status_code == 200
    assert start.json()["mode"] == "mock"
    auth_url = start.json()["auth_url"]
    state = parse_qs(urlparse(auth_url).query)["state"][0]

    first = await client.get(
        "/api/meta-ads/callback",
        params={"state": state, "code": "mock_code"},
        follow_redirects=False,
    )
    assert first.status_code in {302, 307}
    assert "meta_ads=connected" in first.headers["location"]

    replay = await client.get(
        "/api/meta-ads/callback",
        params={"state": state, "code": "mock_code"},
        follow_redirects=False,
    )
    assert replay.status_code == 400
    assert "invalid or expired" in replay.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ads_denied_oauth_consumes_state(client: AsyncClient):
    token = await _register(client, "meta-denied@test.com")
    start = await client.get("/api/meta-ads/connect", headers=_headers(token))
    state = parse_qs(urlparse(start.json()["auth_url"]).query)["state"][0]

    denied = await client.get(
        "/api/meta-ads/callback",
        params={"state": state, "error": "access_denied"},
        follow_redirects=False,
    )
    assert denied.status_code in {302, 307}
    assert "meta_ads=denied" in denied.headers["location"]

    replay = await client.get(
        "/api/meta-ads/callback",
        params={"state": state, "error": "access_denied"},
        follow_redirects=False,
    )
    assert replay.status_code == 400


@pytest.mark.asyncio
async def test_meta_ads_connections_are_workspace_isolated(client: AsyncClient):
    token_one = await _register(client, "meta-workspace-one@test.com")
    token_two = await _register(client, "meta-workspace-two@test.com")
    await client.post("/api/meta-ads/connect-mock", headers=_headers(token_one))

    status_one = await client.get("/api/meta-ads/status", headers=_headers(token_one))
    status_two = await client.get("/api/meta-ads/status", headers=_headers(token_two))
    assert status_one.json()["connected"] is True
    assert status_two.json()["connected"] is False

    accounts_two = await client.get("/api/meta-ads/ad-accounts", headers=_headers(token_two))
    assert accounts_two.status_code == 400


@pytest.mark.asyncio
async def test_meta_ads_unknown_provider_mode_fails_closed(client: AsyncClient, monkeypatch):
    token = await _register(client, "meta-mode@test.com")
    monkeypatch.setattr(settings, "META_ADS_MODE", "unsupported")

    response = await client.get("/api/meta-ads/connect", headers=_headers(token))
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ads_mock_connection_disabled_in_production(client: AsyncClient, monkeypatch):
    token = await _register(client, "meta-production@test.com")
    monkeypatch.setattr(settings, "APP_ENV", "production")

    response = await client.post("/api/meta-ads/connect-mock", headers=_headers(token))
    assert response.status_code == 403
