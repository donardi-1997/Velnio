import json

import pytest

from app.core.config import settings
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError
from app.modules.integrations.infrastructure.meta_ads_ads import RealMetaAdsAdProvider


@pytest.fixture
def real_provider(monkeypatch) -> RealMetaAdsAdProvider:
    monkeypatch.setattr(settings, "META_APP_ID", "test-app-id")
    monkeypatch.setattr(settings, "META_APP_SECRET", "test-app-value")
    monkeypatch.setattr(settings, "META_REDIRECT_URI", "https://example.test/meta/callback")
    return RealMetaAdsAdProvider()


@pytest.mark.asyncio
async def test_real_provider_creates_only_paused_ad_reference(real_provider, monkeypatch):
    captured: dict = {}

    async def fake_list_edge(url, access_token, *, fields, max_pages):
        assert url.endswith("/act_123/ads")
        assert fields == "id,name,status,effective_status,adset_id,creative{id}"
        return []

    async def fake_post_json(url, *, data):
        captured["url"] = url
        captured["data"] = data
        return {"id": "999"}

    monkeypatch.setattr(real_provider, "_list_edge", fake_list_edge)
    monkeypatch.setattr(real_provider, "_post_json", fake_post_json)
    result = await real_provider.ensure_paused_ad(
        "token",
        "act_123",
        "Launch [VELNIO-AD:abc]",
        "456",
        "789",
    )

    assert result["id"] == "999"
    assert result["status"] == "PAUSED"
    assert captured["url"].endswith("/act_123/ads")
    assert captured["data"] == {
        "access_token": "token",
        "name": "Launch [VELNIO-AD:abc]",
        "status": "PAUSED",
        "adset_id": "456",
        "creative": json.dumps({"creative_id": "789"}, separators=(",", ":")),
    }
    assert "daily_budget" not in captured["data"]
    assert "targeting" not in captured["data"]


@pytest.mark.asyncio
async def test_real_provider_reuses_exact_paused_ad(real_provider, monkeypatch):
    async def fake_list_edge(*args, **kwargs):
        return [{
            "id": "999",
            "name": "Launch [VELNIO-AD:abc]",
            "status": "PAUSED",
            "effective_status": "PAUSED",
            "adset_id": "456",
            "creative": {"id": "789"},
        }]

    async def fail_post(*args, **kwargs):
        raise AssertionError("POST must not run for an exact matching Ad")

    monkeypatch.setattr(real_provider, "_list_edge", fake_list_edge)
    monkeypatch.setattr(real_provider, "_post_json", fail_post)
    result = await real_provider.ensure_paused_ad(
        "token", "act_123", "Launch [VELNIO-AD:abc]", "456", "789"
    )
    assert result["id"] == "999"
    assert result["reused"] is True


@pytest.mark.asyncio
async def test_real_provider_refuses_active_matching_ad(real_provider, monkeypatch):
    async def fake_list_edge(*args, **kwargs):
        return [{
            "id": "999",
            "name": "Launch [VELNIO-AD:abc]",
            "status": "ACTIVE",
            "adset_id": "456",
            "creative": {"id": "789"},
        }]

    monkeypatch.setattr(real_provider, "_list_edge", fake_list_edge)
    with pytest.raises(MetaAdsProviderError, match="not paused"):
        await real_provider.ensure_paused_ad(
            "token", "act_123", "Launch [VELNIO-AD:abc]", "456", "789"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("adset_id", "creative_id", "message"),
    [
        ("111", "789", "different Ad Set"),
        ("456", "222", "different AdCreative"),
    ],
)
async def test_real_provider_refuses_matching_name_with_different_relationship(
    real_provider,
    monkeypatch,
    adset_id,
    creative_id,
    message,
):
    async def fake_list_edge(*args, **kwargs):
        return [{
            "id": "999",
            "name": "Launch [VELNIO-AD:abc]",
            "status": "PAUSED",
            "adset_id": adset_id,
            "creative": {"id": creative_id},
        }]

    monkeypatch.setattr(real_provider, "_list_edge", fake_list_edge)
    with pytest.raises(MetaAdsProviderError, match=message):
        await real_provider.ensure_paused_ad(
            "token", "act_123", "Launch [VELNIO-AD:abc]", "456", "789"
        )


@pytest.mark.asyncio
async def test_real_provider_rejects_malformed_relationship_ids_before_network(real_provider, monkeypatch):
    async def fail_list(*args, **kwargs):
        raise AssertionError("network must not run for malformed ids")

    monkeypatch.setattr(real_provider, "_list_edge", fail_list)
    with pytest.raises(MetaAdsProviderError, match="Ad Set id"):
        await real_provider.ensure_paused_ad("token", "act_123", "Ad", "../me", "789")
    with pytest.raises(MetaAdsProviderError, match="AdCreative id"):
        await real_provider.ensure_paused_ad("token", "act_123", "Ad", "456", "creative-x")
