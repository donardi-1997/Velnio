import hashlib
import hmac
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.encryption import decrypt_value
from app.core.exceptions import BadRequestException
from app.models.store import Store, StoreStatus
from app.services.shopify.real_provider import RealShopifyProvider


async def _register(client: AsyncClient, email: str) -> dict:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Test12345!",
            "first_name": "OAuth",
            "last_name": "Shopify",
        },
    )
    assert response.status_code == 201
    return response.json()


class FakeOAuthProvider:
    @staticmethod
    def _normalize_shop_domain(value: str) -> str:
        return RealShopifyProvider._normalize_shop_domain(value)

    def get_install_url(self, shop_domain: str, state: str) -> str:
        return f"https://{shop_domain}/admin/oauth/authorize?state={state}"

    def verify_callback_hmac(self, query_params) -> None:
        if query_params.get("hmac") != "valid":
            raise BadRequestException("Invalid Shopify OAuth callback")

    async def exchange_code(self, code: str, shop_domain: str) -> dict:
        return {
            "access_token": "shpat_test_access",
            "refresh_token": "shprt_test_refresh",
            "expires_in": 3600,
            "refresh_token_expires_in": 7776000,
            "scope": settings.SHOPIFY_SCOPES,
        }

    async def refresh_access_token(self, refresh_token: str, shop_domain: str) -> dict:
        return {
            "access_token": "shpat_refreshed_access",
            "refresh_token": "shprt_refreshed_refresh",
            "expires_in": 3600,
            "refresh_token_expires_in": 7776000,
            "scope": settings.SHOPIFY_SCOPES,
        }

    async def get_shop(self, access_token: str, shop_domain: str) -> dict:
        return {
            "name": "OAuth Test Shop",
            "domain": shop_domain,
            "currency": "COP",
            "country_code": "CO",
        }


def _enable_real_oauth(monkeypatch: pytest.MonkeyPatch, provider=None) -> None:
    monkeypatch.setattr(settings, "SHOPIFY_MODE", "real")
    monkeypatch.setattr(settings, "SHOPIFY_API_KEY", "test-client-id")
    monkeypatch.setattr(settings, "SHOPIFY_API_SECRET", "test-client-secret")
    monkeypatch.setattr(settings, "SHOPIFY_REDIRECT_URI", "http://test/api/stores/shopify/callback")
    monkeypatch.setattr(
        "app.modules.commerce.application.shopify_connection.get_shopify_provider",
        lambda: provider or FakeOAuthProvider(),
    )


@pytest.mark.asyncio
async def test_shopify_oauth_connect_callback_persists_encrypted_expiring_credentials(
    client: AsyncClient,
    db_session,
    monkeypatch: pytest.MonkeyPatch,
):
    _enable_real_oauth(monkeypatch)
    auth = await _register(client, "shopify-oauth-success@test.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    start = await client.post(
        "/api/stores/shopify/connect",
        json={"shop_domain": "oauth-test.myshopify.com"},
        headers=headers,
    )
    assert start.status_code == 200
    state = parse_qs(urlparse(start.json()["auth_url"]).query)["state"][0]

    callback = await client.get(
        "/api/stores/shopify/callback",
        params={
            "shop": "oauth-test.myshopify.com",
            "code": "authorization-code",
            "state": state,
            "hmac": "valid",
            "timestamp": "1",
        },
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert callback.headers["location"].endswith("/stores?shopify=connected")

    store = (
        await db_session.execute(select(Store).where(Store.shop_domain == "oauth-test.myshopify.com"))
    ).scalar_one()
    assert store.status == StoreStatus.CONNECTED
    assert store.currency == "COP"
    assert store.country == "CO"
    assert store.access_token_encrypted != "shpat_test_access"
    assert store.refresh_token_encrypted != "shprt_test_refresh"
    assert decrypt_value(store.access_token_encrypted) == "shpat_test_access"
    assert decrypt_value(store.refresh_token_encrypted) == "shprt_test_refresh"
    assert store.token_expires_at is not None
    assert store.refresh_token_expires_at is not None


@pytest.mark.asyncio
async def test_shopify_oauth_state_is_single_use(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    _enable_real_oauth(monkeypatch)
    auth = await _register(client, "shopify-oauth-replay@test.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    start = await client.post(
        "/api/stores/shopify/connect",
        json={"shop_domain": "replay-test.myshopify.com"},
        headers=headers,
    )
    state = parse_qs(urlparse(start.json()["auth_url"]).query)["state"][0]
    params = {"shop": "replay-test.myshopify.com", "code": "code", "state": state, "hmac": "valid"}

    first = await client.get("/api/stores/shopify/callback", params=params, follow_redirects=False)
    second = await client.get("/api/stores/shopify/callback", params=params, follow_redirects=False)

    assert first.status_code == 302
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_shopify_oauth_rejects_shop_mismatch(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    _enable_real_oauth(monkeypatch)
    auth = await _register(client, "shopify-oauth-mismatch@test.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    start = await client.post(
        "/api/stores/shopify/connect",
        json={"shop_domain": "expected-shop.myshopify.com"},
        headers=headers,
    )
    state = parse_qs(urlparse(start.json()["auth_url"]).query)["state"][0]

    response = await client.get(
        "/api/stores/shopify/callback",
        params={"shop": "other-shop.myshopify.com", "code": "code", "state": state, "hmac": "valid"},
        follow_redirects=False,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_shopify_oauth_rejects_incomplete_scopes(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    provider = FakeOAuthProvider()

    async def exchange_code(code: str, shop_domain: str) -> dict:
        return {
            "access_token": "shpat_test",
            "refresh_token": "shprt_test",
            "expires_in": 3600,
            "refresh_token_expires_in": 7776000,
            "scope": "read_products",
        }

    provider.exchange_code = exchange_code
    _enable_real_oauth(monkeypatch, provider)
    auth = await _register(client, "shopify-oauth-scopes@test.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    start = await client.post(
        "/api/stores/shopify/connect",
        json={"shop_domain": "scope-test.myshopify.com"},
        headers=headers,
    )
    state = parse_qs(urlparse(start.json()["auth_url"]).query)["state"][0]

    response = await client.get(
        "/api/stores/shopify/callback",
        params={"shop": "scope-test.myshopify.com", "code": "code", "state": state, "hmac": "valid"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "required permissions" in response.json()["detail"].lower()


def test_real_shopify_hmac_verification(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "SHOPIFY_API_KEY", "key")
    monkeypatch.setattr(settings, "SHOPIFY_API_SECRET", "secret")
    monkeypatch.setattr(settings, "SHOPIFY_REDIRECT_URI", "https://app.example.com/callback")
    params = {
        "code": "abc",
        "shop": "valid-shop.myshopify.com",
        "state": "nonce",
        "timestamp": "123456",
    }
    message = "&".join(f"{key}={value}" for key, value in sorted(params.items()))
    params["hmac"] = hmac.new(b"secret", message.encode(), hashlib.sha256).hexdigest()

    RealShopifyProvider().verify_callback_hmac(params)

    params["hmac"] = "0" * 64
    with pytest.raises(BadRequestException):
        RealShopifyProvider().verify_callback_hmac(params)


def test_real_shopify_install_url_is_shop_scoped_and_contains_state(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "SHOPIFY_API_KEY", "key")
    monkeypatch.setattr(settings, "SHOPIFY_API_SECRET", "secret")
    monkeypatch.setattr(settings, "SHOPIFY_REDIRECT_URI", "https://app.example.com/api/stores/shopify/callback")
    url = RealShopifyProvider().get_install_url("valid-shop.myshopify.com", "signed-state")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.netloc == "valid-shop.myshopify.com"
    assert parsed.path == "/admin/oauth/authorize"
    assert query["client_id"] == ["key"]
    assert query["state"] == ["signed-state"]
    assert query["redirect_uri"] == ["https://app.example.com/api/stores/shopify/callback"]
