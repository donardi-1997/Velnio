import json

import pytest

from app.core.config import settings
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError
from app.modules.integrations.infrastructure.meta_ads_creatives import RealMetaAdsCreativeProvider


@pytest.fixture
def real_provider(monkeypatch) -> RealMetaAdsCreativeProvider:
    monkeypatch.setattr(settings, "META_APP_ID", "test-app-id")
    monkeypatch.setattr(settings, "META_APP_SECRET", "test-app-value")
    monkeypatch.setattr(settings, "META_REDIRECT_URI", "https://example.test/meta/callback")
    return RealMetaAdsCreativeProvider()


@pytest.mark.asyncio
async def test_real_provider_creates_only_standalone_adcreative(real_provider, monkeypatch):
    captured: dict = {}

    async def fake_list_edge(url, access_token, *, fields, max_pages):
        assert url.endswith("/act_123/adcreatives")
        assert fields == "id,name,object_story_spec"
        return []

    async def fake_post_json(url, *, data):
        captured["url"] = url
        captured["data"] = data
        return {"id": "987654321"}

    monkeypatch.setattr(real_provider, "_list_edge", fake_list_edge)
    monkeypatch.setattr(real_provider, "_post_json", fake_post_json)

    result = await real_provider.ensure_standalone_creative(
        "token",
        "act_123",
        "Launch [VELNIO-CREATIVE:abc]",
        "456",
        "789",
        "https://shop.myshopify.com/pages/launch",
        "https://cdn.example.test/launch.jpg",
        "Primary copy",
        "Headline",
        "SHOP_NOW",
    )

    assert result["id"] == "987654321"
    assert result["reused"] is False
    assert captured["url"].endswith("/act_123/adcreatives")
    assert not captured["url"].endswith("/ads")
    data = captured["data"]
    assert "status" not in data
    assert "adset_id" not in data
    assert "creative" not in data
    story = json.loads(data["object_story_spec"])
    assert story["page_id"] == "456"
    assert story["instagram_actor_id"] == "789"
    assert story["link_data"] == {
        "call_to_action": {"type": "SHOP_NOW"},
        "link": "https://shop.myshopify.com/pages/launch",
        "message": "Primary copy",
        "picture": "https://cdn.example.test/launch.jpg",
        "name": "Headline",
    }


@pytest.mark.asyncio
async def test_real_provider_omits_optional_instagram_and_headline(real_provider, monkeypatch):
    captured: dict = {}

    async def fake_list_edge(*args, **kwargs):
        return []

    async def fake_post_json(url, *, data):
        captured["data"] = data
        return {"id": "987"}

    monkeypatch.setattr(real_provider, "_list_edge", fake_list_edge)
    monkeypatch.setattr(real_provider, "_post_json", fake_post_json)
    await real_provider.ensure_standalone_creative(
        "token",
        "act_123",
        "Creative",
        "456",
        None,
        "https://shop.myshopify.com/pages/launch",
        "https://cdn.example.test/launch.jpg",
        "Primary copy",
        None,
        "LEARN_MORE",
    )
    story = json.loads(captured["data"]["object_story_spec"])
    assert "instagram_actor_id" not in story
    assert "name" not in story["link_data"]
    assert story["link_data"]["call_to_action"]["type"] == "LEARN_MORE"


@pytest.mark.asyncio
async def test_real_provider_reuses_exact_matching_creative(real_provider, monkeypatch):
    async def fake_list_edge(*args, **kwargs):
        return [{
            "id": "987",
            "name": "Launch [VELNIO-CREATIVE:abc]",
            "object_story_spec": {
                "page_id": "456",
                "instagram_actor_id": "789",
                "link_data": {
                    "link": "https://shop.myshopify.com/pages/launch",
                    "picture": "https://cdn.example.test/launch.jpg",
                    "message": "Primary copy",
                    "name": "Headline",
                    "call_to_action": {"type": "SHOP_NOW"},
                },
            },
        }]

    async def fail_post(*args, **kwargs):
        raise AssertionError("POST must not run for an exact matching Creative")

    monkeypatch.setattr(real_provider, "_list_edge", fake_list_edge)
    monkeypatch.setattr(real_provider, "_post_json", fail_post)
    result = await real_provider.ensure_standalone_creative(
        "token",
        "act_123",
        "Launch [VELNIO-CREATIVE:abc]",
        "456",
        "789",
        "https://shop.myshopify.com/pages/launch",
        "https://cdn.example.test/launch.jpg",
        "Primary copy",
        "Headline",
        "SHOP_NOW",
    )
    assert result["id"] == "987"
    assert result["reused"] is True


@pytest.mark.asyncio
async def test_real_provider_refuses_matching_name_with_different_destination(real_provider, monkeypatch):
    async def fake_list_edge(*args, **kwargs):
        return [{
            "id": "987",
            "name": "Launch [VELNIO-CREATIVE:abc]",
            "object_story_spec": {
                "page_id": "456",
                "link_data": {
                    "link": "https://other.example.test/landing",
                    "picture": "https://cdn.example.test/launch.jpg",
                    "message": "Primary copy",
                    "name": "Headline",
                    "call_to_action": {"type": "SHOP_NOW"},
                },
            },
        }]

    monkeypatch.setattr(real_provider, "_list_edge", fake_list_edge)
    with pytest.raises(MetaAdsProviderError, match="different destination"):
        await real_provider.ensure_standalone_creative(
            "token",
            "act_123",
            "Launch [VELNIO-CREATIVE:abc]",
            "456",
            None,
            "https://shop.myshopify.com/pages/launch",
            "https://cdn.example.test/launch.jpg",
            "Primary copy",
            "Headline",
            "SHOP_NOW",
        )


@pytest.mark.asyncio
async def test_real_provider_rejects_non_https_destination_before_network(real_provider, monkeypatch):
    async def fail_list(*args, **kwargs):
        raise AssertionError("network must not run for invalid inputs")

    monkeypatch.setattr(real_provider, "_list_edge", fail_list)
    with pytest.raises(MetaAdsProviderError, match="HTTPS"):
        await real_provider.ensure_standalone_creative(
            "token",
            "act_123",
            "Creative",
            "456",
            None,
            "http://shop.myshopify.com/pages/launch",
            "https://cdn.example.test/launch.jpg",
            "Primary copy",
            None,
            "SHOP_NOW",
        )
