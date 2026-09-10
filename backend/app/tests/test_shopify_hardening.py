import httpx
import pytest
from httpx import AsyncClient

from app.core.encryption import encrypt_value
from app.core.exceptions import BadGatewayException, BadRequestException
from app.models.store import Store, StoreStatus
from app.services.shopify.real_provider import RealShopifyProvider


async def _register(client: AsyncClient, email: str) -> dict:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Test12345!",
            "first_name": "Shopify",
            "last_name": "Hardening",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize(
    "shop_domain",
    [
        "https://safe-shop.myshopify.com",
        "safe-shop.myshopify.com/path",
        "safe-shop.myshopify.com.evil.test",
        "evil.test",
        "safe-shop.myshopify.com:443",
        "",
    ],
)
def test_real_shopify_provider_rejects_unsafe_shop_domains(shop_domain: str):
    with pytest.raises(BadRequestException):
        RealShopifyProvider._normalize_shop_domain(shop_domain)


def test_real_shopify_provider_normalizes_valid_shop_domain():
    assert (
        RealShopifyProvider._normalize_shop_domain(" Safe-Shop.MyShopify.Com. ")
        == "safe-shop.myshopify.com"
    )


def test_real_shopify_provider_decrypts_store_token_before_use():
    store = Store(
        name="Safe Store",
        shop_domain="safe-shop.myshopify.com",
        status=StoreStatus.CONNECTED,
        access_token_encrypted=encrypt_value("shpat_plaintext_secret"),
        country="US",
        currency="USD",
    )

    token, domain = RealShopifyProvider()._store_credentials(store)

    assert token == "shpat_plaintext_secret"
    assert token != store.access_token_encrypted
    assert domain == "safe-shop.myshopify.com"


def test_real_shopify_provider_rejects_disconnected_store():
    store = Store(
        name="Disconnected",
        shop_domain="safe-shop.myshopify.com",
        status=StoreStatus.DISCONNECTED,
        access_token_encrypted=encrypt_value("secret"),
        country="US",
        currency="USD",
    )

    with pytest.raises(BadRequestException) as exc_info:
        RealShopifyProvider()._store_credentials(store)

    assert "not connected" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_real_shopify_timeout_is_sanitized(monkeypatch: pytest.MonkeyPatch):
    class TimeoutClient:
        def __init__(self, **kwargs):
            assert kwargs["timeout"] == 15.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, **kwargs):
            request = httpx.Request(method, url)
            raise httpx.ConnectTimeout(
                "token=do-not-leak sensitive-network-detail",
                request=request,
            )

    monkeypatch.setattr(
        "app.services.shopify.real_provider.httpx.AsyncClient",
        TimeoutClient,
    )

    with pytest.raises(BadGatewayException) as exc_info:
        await RealShopifyProvider().get_shop(
            "shpat_super_secret",
            "safe-shop.myshopify.com",
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Shopify request timed out; try again"
    assert "secret" not in exc_info.value.detail
    assert "do-not-leak" not in exc_info.value.detail


@pytest.mark.asyncio
async def test_real_shopify_auth_error_is_sanitized(monkeypatch: pytest.MonkeyPatch):
    class UnauthorizedClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, **kwargs):
            request = httpx.Request(method, url)
            return httpx.Response(
                401,
                request=request,
                text="access_token=do-not-leak shopify-secret-body",
            )

    monkeypatch.setattr(
        "app.services.shopify.real_provider.httpx.AsyncClient",
        UnauthorizedClient,
    )

    with pytest.raises(BadGatewayException) as exc_info:
        await RealShopifyProvider().get_shop(
            "shpat_super_secret",
            "safe-shop.myshopify.com",
        )

    assert exc_info.value.detail == "Shopify authorization failed; reconnect your store"
    assert "do-not-leak" not in exc_info.value.detail


@pytest.mark.asyncio
async def test_real_shopify_invalid_json_is_sanitized(monkeypatch: pytest.MonkeyPatch):
    class InvalidJsonClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, **kwargs):
            request = httpx.Request(method, url)
            return httpx.Response(200, request=request, content=b"not-json")

    monkeypatch.setattr(
        "app.services.shopify.real_provider.httpx.AsyncClient",
        InvalidJsonClient,
    )

    with pytest.raises(BadGatewayException) as exc_info:
        await RealShopifyProvider().get_shop(
            "token",
            "safe-shop.myshopify.com",
        )

    assert exc_info.value.detail == "Shopify returned an invalid response"


@pytest.mark.asyncio
async def test_product_publish_is_idempotent(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    auth = await _register(client, "shopify-product-idempotency@test.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    product_response = await client.post(
        "/api/products",
        json={"name": "Idempotent Product", "selling_price": 29.99},
        headers=headers,
    )
    assert product_response.status_code == 201
    product_id = product_response.json()["id"]

    calls = {"count": 0}

    class CountingProvider:
        async def publish_product(self, product, store=None):
            calls["count"] += 1
            return {
                "provider": "test",
                "shopify_product_id": "remote-product-123",
                "shopify_page_id": None,
            }

    monkeypatch.setattr(
        "app.modules.commerce.application.publishing.get_shopify_provider",
        lambda: CountingProvider(),
    )

    first = await client.post(f"/api/products/{product_id}/publish", headers=headers)
    second = await client.post(f"/api/products/{product_id}/publish", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["shopify_product_id"] == "remote-product-123"
    assert second.json()["shopify_product_id"] == "remote-product-123"
    assert second.json()["provider"] == "existing"
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_product_publish_sanitizes_unexpected_provider_error(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    auth = await _register(client, "shopify-product-error@test.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    product_response = await client.post(
        "/api/products",
        json={"name": "Provider Error Product"},
        headers=headers,
    )
    product_id = product_response.json()["id"]

    class FailingProvider:
        async def publish_product(self, product, store=None):
            raise RuntimeError("access_token=do-not-leak remote-body-secret")

    monkeypatch.setattr(
        "app.modules.commerce.application.publishing.get_shopify_provider",
        lambda: FailingProvider(),
    )

    response = await client.post(f"/api/products/{product_id}/publish", headers=headers)

    assert response.status_code == 502
    assert response.json()["detail"] == "Shopify publish failed; try again"
    assert "do-not-leak" not in response.text
