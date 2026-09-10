from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import BadRequestException
from app.services.shopify.real_provider import RealShopifyProvider


@pytest.mark.asyncio
async def test_create_product_reuses_owned_remote_resource(monkeypatch: pytest.MonkeyPatch):
    provider = RealShopifyProvider()
    handle = "velnio-product-123"
    ownership_tag = "velnio-product:123"
    calls = []

    async def fake_graphql(access_token, shop_domain, query, variables=None):
        calls.append(query)
        if "VelnioProductByHandle" in query:
            return {
                "product": {
                    "id": "gid://shopify/Product/1",
                    "title": "Old",
                    "handle": handle,
                    "status": "ACTIVE",
                    "tags": [ownership_tag, "merchant-added"],
                    "variants": {"nodes": [{"id": "gid://shopify/ProductVariant/1"}]},
                }
            }
        if "VelnioUpdateProduct" in query:
            assert "merchant-added" in variables["product"]["tags"]
            return {
                "productUpdate": {
                    "product": {
                        "id": "gid://shopify/Product/1",
                        "title": "Updated",
                        "handle": handle,
                        "status": "ACTIVE",
                        "tags": variables["product"]["tags"],
                        "variants": {"nodes": [{"id": "gid://shopify/ProductVariant/1"}]},
                    },
                    "userErrors": [],
                }
            }
        raise AssertionError(f"unexpected graphql call: {query}")

    async def no_publish(*args, **kwargs):
        return None

    monkeypatch.setattr(provider, "_graphql", fake_graphql)
    monkeypatch.setattr(provider, "_publish_product_to_online_store", no_publish)

    result = await provider.create_product(
        "token",
        "shop.myshopify.com",
        {
            "title": "Updated",
            "handle": handle,
            "ownership_tag": ownership_tag,
            "tags": ["velnio", ownership_tag],
        },
    )

    assert result["id"] == "gid://shopify/Product/1"
    assert any("VelnioUpdateProduct" in query for query in calls)
    assert not any("VelnioCreateProduct" in query for query in calls)


@pytest.mark.asyncio
async def test_create_product_never_adopts_foreign_handle(monkeypatch: pytest.MonkeyPatch):
    provider = RealShopifyProvider()

    async def fake_graphql(access_token, shop_domain, query, variables=None):
        return {
            "product": {
                "id": "gid://shopify/Product/9",
                "handle": "velnio-product-123",
                "tags": ["merchant-owned"],
                "variants": {"nodes": []},
            }
        }

    monkeypatch.setattr(provider, "_graphql", fake_graphql)

    with pytest.raises(BadRequestException, match="handle conflicts"):
        await provider.create_product(
            "token",
            "shop.myshopify.com",
            {
                "title": "Product",
                "handle": "velnio-product-123",
                "ownership_tag": "velnio-product:123",
                "tags": ["velnio", "velnio-product:123"],
            },
        )


@pytest.mark.asyncio
async def test_create_page_reuses_owned_remote_resource(monkeypatch: pytest.MonkeyPatch):
    provider = RealShopifyProvider()
    handle = "velnio-campaign-123"
    marker = "velnio-campaign:123"
    calls = []

    async def fake_graphql(access_token, shop_domain, query, variables=None):
        calls.append(query)
        if "VelnioPageByHandle" in query:
            return {
                "pages": {
                    "nodes": [
                        {
                            "id": "gid://shopify/Page/1",
                            "title": "Old",
                            "handle": handle,
                            "body": f"<!-- {marker} -->\n<p>old</p>",
                        }
                    ]
                }
            }
        if "VelnioUpdatePage" in query:
            assert f"<!-- {marker} -->" in variables["page"]["body"]
            return {
                "pageUpdate": {
                    "page": {
                        "id": "gid://shopify/Page/1",
                        "title": "New",
                        "handle": handle,
                    },
                    "userErrors": [],
                }
            }
        raise AssertionError(f"unexpected graphql call: {query}")

    monkeypatch.setattr(provider, "_graphql", fake_graphql)

    result = await provider.create_page(
        "token",
        "shop.myshopify.com",
        {
            "title": "New",
            "body_html": "<p>new</p>",
            "published": True,
            "handle": handle,
            "ownership_marker": marker,
        },
    )

    assert result["id"] == "gid://shopify/Page/1"
    assert any("VelnioUpdatePage" in query for query in calls)
    assert not any("VelnioCreatePage" in query for query in calls)


@pytest.mark.asyncio
async def test_create_page_never_overwrites_foreign_handle(monkeypatch: pytest.MonkeyPatch):
    provider = RealShopifyProvider()

    async def fake_graphql(access_token, shop_domain, query, variables=None):
        return {
            "pages": {
                "nodes": [
                    {
                        "id": "gid://shopify/Page/9",
                        "title": "Merchant page",
                        "handle": "velnio-campaign-123",
                        "body": "<p>merchant content</p>",
                    }
                ]
            }
        }

    monkeypatch.setattr(provider, "_graphql", fake_graphql)

    with pytest.raises(BadRequestException, match="handle conflicts"):
        await provider.create_page(
            "token",
            "shop.myshopify.com",
            {
                "title": "Campaign",
                "body_html": "<p>velnio</p>",
                "handle": "velnio-campaign-123",
                "ownership_marker": "velnio-campaign:123",
            },
        )


@pytest.mark.asyncio
async def test_publish_product_uses_stable_remote_identity(monkeypatch: pytest.MonkeyPatch):
    provider = RealShopifyProvider()
    product_id = uuid4()
    captured = {}

    monkeypatch.setattr(provider, "_store_credentials", lambda store: ("token", "shop.myshopify.com"))

    async def fake_create_product(access_token, shop_domain, product_data):
        captured.update(product_data)
        return {"id": "gid://shopify/Product/1"}

    monkeypatch.setattr(provider, "create_product", fake_create_product)

    product = SimpleNamespace(id=product_id, name="Widget", description="", images=[])
    await provider.publish_product(product, SimpleNamespace())

    assert captured["handle"] == f"velnio-product-{product_id}"
    assert captured["ownership_tag"] == f"velnio-product:{product_id}"
    assert captured["ownership_tag"] in captured["tags"]


def test_stable_handle_is_deterministic():
    resource_id = uuid4()
    provider = RealShopifyProvider()
    assert provider._stable_handle("campaign", resource_id) == provider._stable_handle("campaign", resource_id)
