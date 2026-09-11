import json

import pytest

from app.core.config import settings
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError, RealMetaAdsProvider


@pytest.fixture
def real_provider(monkeypatch) -> RealMetaAdsProvider:
    monkeypatch.setattr(settings, "META_APP_ID", "test-app-id")
    monkeypatch.setattr(settings, "META_APP_SECRET", "test-app-value")
    monkeypatch.setattr(settings, "META_REDIRECT_URI", "https://example.test/meta/callback")
    return RealMetaAdsProvider()


@pytest.mark.asyncio
async def test_real_provider_creates_paused_ad_set_with_expected_payload(real_provider, monkeypatch):
    captured: dict = {}

    async def fake_list_edge(url, access_token, *, fields, max_pages):
        assert url.endswith("/act_123/adsets")
        return []

    async def fake_post_json(url, *, data):
        captured["url"] = url
        captured["data"] = data
        return {"id": "987654321"}

    monkeypatch.setattr(real_provider, "_list_edge", fake_list_edge)
    monkeypatch.setattr(real_provider, "_post_json", fake_post_json)

    result = await real_provider.ensure_paused_ad_set(
        "token", "act_123", "456", "Launch [VELNIO-ADSET:abc]", 2500, "CO", "789"
    )

    assert result["status"] == "PAUSED"
    assert captured["url"].endswith("/act_123/adsets")
    data = captured["data"]
    assert data["status"] == "PAUSED"
    assert data["campaign_id"] == "456"
    assert data["daily_budget"] == "2500"
    assert data["billing_event"] == "IMPRESSIONS"
    assert data["optimization_goal"] == "OFFSITE_CONVERSIONS"
    assert data["bid_strategy"] == "LOWEST_COST_WITHOUT_CAP"
    assert json.loads(data["targeting"])["geo_locations"]["countries"] == ["CO"]
    assert json.loads(data["promoted_object"]) == {
        "pixel_id": "789",
        "custom_event_type": "PURCHASE",
    }
    assert "start_time" not in data
    assert "creative" not in data


@pytest.mark.asyncio
async def test_real_provider_reuses_only_exact_paused_ad_set(real_provider, monkeypatch):
    async def fake_list_edge(url, access_token, *, fields, max_pages):
        return [{
            "id": "987",
            "name": "Launch [VELNIO-ADSET:abc]",
            "status": "PAUSED",
            "campaign_id": "456",
            "daily_budget": "2500",
            "optimization_goal": "OFFSITE_CONVERSIONS",
            "billing_event": "IMPRESSIONS",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "targeting": {"geo_locations": {"countries": ["CO"]}},
            "promoted_object": {"pixel_id": "789", "custom_event_type": "PURCHASE"},
        }]

    async def fail_post(*args, **kwargs):
        raise AssertionError("POST must not run when exact PAUSED Ad Set exists")

    monkeypatch.setattr(real_provider, "_list_edge", fake_list_edge)
    monkeypatch.setattr(real_provider, "_post_json", fail_post)
    result = await real_provider.ensure_paused_ad_set(
        "token", "act_123", "456", "Launch [VELNIO-ADSET:abc]", 2500, "CO", "789"
    )
    assert result["id"] == "987"
    assert result["reused"] is True


@pytest.mark.asyncio
async def test_real_provider_refuses_non_paused_matching_ad_set(real_provider, monkeypatch):
    async def fake_list_edge(url, access_token, *, fields, max_pages):
        return [{
            "id": "987",
            "name": "Launch [VELNIO-ADSET:abc]",
            "status": "ACTIVE",
            "campaign_id": "456",
            "daily_budget": "2500",
            "optimization_goal": "OFFSITE_CONVERSIONS",
            "billing_event": "IMPRESSIONS",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "targeting": {"geo_locations": {"countries": ["CO"]}},
            "promoted_object": {"pixel_id": "789", "custom_event_type": "PURCHASE"},
        }]

    monkeypatch.setattr(real_provider, "_list_edge", fake_list_edge)
    with pytest.raises(MetaAdsProviderError, match="not paused"):
        await real_provider.ensure_paused_ad_set(
            "token", "act_123", "456", "Launch [VELNIO-ADSET:abc]", 2500, "CO", "789"
        )


@pytest.mark.asyncio
async def test_real_provider_refuses_matching_ad_set_with_different_budget(real_provider, monkeypatch):
    async def fake_list_edge(url, access_token, *, fields, max_pages):
        return [{
            "id": "987",
            "name": "Launch [VELNIO-ADSET:abc]",
            "status": "PAUSED",
            "campaign_id": "456",
            "daily_budget": "9999",
            "optimization_goal": "OFFSITE_CONVERSIONS",
            "billing_event": "IMPRESSIONS",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "targeting": {"geo_locations": {"countries": ["CO"]}},
            "promoted_object": {"pixel_id": "789", "custom_event_type": "PURCHASE"},
        }]

    monkeypatch.setattr(real_provider, "_list_edge", fake_list_edge)
    with pytest.raises(MetaAdsProviderError, match="different budget"):
        await real_provider.ensure_paused_ad_set(
            "token", "act_123", "456", "Launch [VELNIO-ADSET:abc]", 2500, "CO", "789"
        )
