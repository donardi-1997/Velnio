import pytest

from app.core.config import settings
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError
from app.modules.integrations.infrastructure.meta_ads_status import RealMetaAdsStatusProvider


@pytest.fixture
def real_provider(monkeypatch) -> RealMetaAdsStatusProvider:
    monkeypatch.setattr(settings, "META_APP_ID", "test-app-id")
    monkeypatch.setattr(settings, "META_APP_SECRET", "test-app-value")
    monkeypatch.setattr(settings, "META_REDIRECT_URI", "https://example.test/meta/callback")
    return RealMetaAdsStatusProvider()


@pytest.mark.asyncio
async def test_real_provider_reads_live_ad_hierarchy_and_prefers_configured_status(
    real_provider,
    monkeypatch,
):
    captured: dict = {}

    async def fake_get_json(url, *, params):
        captured["url"] = url
        captured["params"] = params
        return {
            "id": "444",
            "account_id": "1001",
            "campaign_id": "111",
            "adset_id": "222",
            "configured_status": "ACTIVE",
            "status": "PAUSED",
            "effective_status": "CAMPAIGN_PAUSED",
            "creative": {"id": "333"},
        }

    monkeypatch.setattr(real_provider, "_get_json", fake_get_json)
    state = await real_provider.get_ad_state(
        "token",
        "act_1001",
        "111",
        "222",
        "333",
        "444",
    )

    assert captured["url"].endswith("/444")
    assert captured["params"]["fields"] == (
        "id,account_id,campaign_id,adset_id,configured_status,status,effective_status,creative"
    )
    assert state == {
        "id": "444",
        "account_id": "1001",
        "campaign_id": "111",
        "adset_id": "222",
        "creative_id": "333",
        "status": "ACTIVE",
        "effective_status": "CAMPAIGN_PAUSED",
    }


@pytest.mark.asyncio
async def test_real_provider_rejects_malformed_ad_relationship(real_provider, monkeypatch):
    async def fake_get_json(url, *, params):
        return {
            "id": "444",
            "account_id": "1001",
            "campaign_id": "111",
            "adset_id": "222",
            "configured_status": "PAUSED",
            "effective_status": "PAUSED",
            "creative": {},
        }

    monkeypatch.setattr(real_provider, "_get_json", fake_get_json)
    with pytest.raises(MetaAdsProviderError, match="AdCreative relationship"):
        await real_provider.get_ad_state(
            "token",
            "act_1001",
            "111",
            "222",
            "333",
            "444",
        )


@pytest.mark.asyncio
async def test_real_provider_rejects_invalid_remote_id_before_network(real_provider, monkeypatch):
    async def fail_get(*args, **kwargs):
        raise AssertionError("network must not run for invalid remote IDs")

    monkeypatch.setattr(real_provider, "_get_json", fail_get)
    with pytest.raises(MetaAdsProviderError, match="Invalid Meta Ad id"):
        await real_provider.get_ad_state(
            "token",
            "act_1001",
            "111",
            "222",
            "333",
            "not-an-id",
        )
