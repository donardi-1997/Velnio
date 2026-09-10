import pytest

from app.core.exceptions import BadRequestException
from app.services.shopify.real_provider import RealShopifyProvider


@pytest.mark.asyncio
async def test_online_store_publication_is_selected_by_stable_channel_handle(monkeypatch):
    provider = RealShopifyProvider()
    publication_query = None

    async def fake_graphql(access_token, shop_domain, query, variables=None):
        nonlocal publication_query
        if "VelnioPublications" in query:
            publication_query = query
            return {
                "publications": {
                    "nodes": [
                        {
                            "id": "gid://shopify/Publication/pos",
                            "autoPublish": False,
                            "channels": {"nodes": [{"handle": "point_of_sale"}]},
                        },
                        {
                            "id": "gid://shopify/Publication/online",
                            "autoPublish": False,
                            "channels": {"nodes": [{"handle": "online_store"}]},
                        },
                    ]
                }
            }
        if "VelnioPublicationStatus" in query:
            assert variables == {
                "id": "gid://shopify/Product/123",
                "publicationId": "gid://shopify/Publication/online",
            }
            return {"node": {"publishedOnPublication": True}}
        raise AssertionError(f"Unexpected GraphQL operation: {query}")

    monkeypatch.setattr(provider, "_graphql", fake_graphql)

    await provider._publish_product_to_online_store(
        "token",
        "example.myshopify.com",
        "gid://shopify/Product/123",
    )

    assert publication_query is not None
    assert "catalogType: APP" in publication_query
    assert "channels(first: 5)" in publication_query
    assert "name" not in publication_query


@pytest.mark.asyncio
async def test_online_store_publication_works_when_other_channel_names_are_irrelevant(monkeypatch):
    provider = RealShopifyProvider()
    published = False

    async def fake_graphql(access_token, shop_domain, query, variables=None):
        nonlocal published
        if "VelnioPublications" in query:
            return {
                "publications": {
                    "nodes": [
                        {
                            "id": "gid://shopify/Publication/online",
                            "channels": {"nodes": [{"handle": "online_store"}]},
                        }
                    ]
                }
            }
        if "VelnioPublicationStatus" in query:
            return {"node": {"publishedOnPublication": False}}
        if "VelnioPublishProduct" in query:
            assert variables == {
                "id": "gid://shopify/Product/456",
                "input": [{"publicationId": "gid://shopify/Publication/online"}],
            }
            published = True
            return {"publishablePublish": {"userErrors": []}}
        raise AssertionError(f"Unexpected GraphQL operation: {query}")

    monkeypatch.setattr(provider, "_graphql", fake_graphql)

    await provider._publish_product_to_online_store(
        "token",
        "example.myshopify.com",
        "gid://shopify/Product/456",
    )

    assert published is True


@pytest.mark.asyncio
async def test_missing_online_store_channel_fails_closed(monkeypatch):
    provider = RealShopifyProvider()

    async def fake_graphql(access_token, shop_domain, query, variables=None):
        assert "VelnioPublications" in query
        return {
            "publications": {
                "nodes": [
                    {
                        "id": "gid://shopify/Publication/pos",
                        "channels": {"nodes": [{"handle": "point_of_sale"}]},
                    }
                ]
            }
        }

    monkeypatch.setattr(provider, "_graphql", fake_graphql)

    with pytest.raises(BadRequestException) as exc_info:
        await provider._publish_product_to_online_store(
            "token",
            "example.myshopify.com",
            "gid://shopify/Product/789",
        )

    assert exc_info.value.detail == "Shopify Online Store sales channel is required to publish products"
