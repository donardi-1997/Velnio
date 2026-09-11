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
async def test_real_provider_reads_campaign_state_with_ownership_fields(real_provider, monkeypatch):
    captured: dict = {}

    async def fake_get_json(url, *, params):
        captured["url"] = url
        captured["params"] = params
        return {
            "123": {
                "id": "123",
                "account_id": "456",
                "configured_status": "PAUSED",
                "effective_status": "PAUSED",
            }
        }

    monkeypatch.setattr(real_provider, "_get_json", fake_get_json)
    state = await real_provider.get_campaign_state("token", "act_456", "123")

    assert captured["url"] == real_provider.graph_base
    assert captured["params"]["ids"] == "123"
    assert captured["params"]["fields"] == "id,account_id,status,configured_status,effective_status"
    assert state == {
        "id": "123",
        "account_id": "456",
        "status": "PAUSED",
        "effective_status": "PAUSED",
    }


@pytest.mark.asyncio
async def test_real_provider_reads_ad_set_state_with_campaign_and_account(real_provider, monkeypatch):
    captured: dict = {}

    async def fake_get_json(url, *, params):
        captured["url"] = url
        captured["params"] = params
        return {
            "id": "789",
            "account_id": "456",
            "campaign_id": "123",
            "status": "PAUSED",
            "effective_status": "PAUSED",
        }

    monkeypatch.setattr(real_provider, "_get_json", fake_get_json)
    state = await real_provider.get_ad_set_state("token", "act_456", "123", "789")

    assert captured["url"].endswith("/789")
    assert captured["params"]["fields"] == "id,account_id,campaign_id,status,effective_status"
    assert state["account_id"] == "456"
    assert state["campaign_id"] == "123"
    assert state["status"] == "PAUSED"


@pytest.mark.asyncio
async def test_real_provider_rejects_malformed_remote_ids_before_network(real_provider, monkeypatch):
    async def fail_get(*args, **kwargs):
        raise AssertionError("network must not run for malformed ids")

    monkeypatch.setattr(real_provider, "_get_json", fail_get)
    with pytest.raises(MetaAdsProviderError, match="Campaign id"):
        await real_provider.get_campaign_state("token", "act_456", "../me")
    with pytest.raises(MetaAdsProviderError, match="Ad Set id"):
        await real_provider.get_ad_set_state("token", "act_456", "123", "not-numeric")


@pytest.mark.asyncio
async def test_real_provider_rejects_mismatched_campaign_payload(real_provider, monkeypatch):
    async def fake_get_json(*args, **kwargs):
        return {
            "123": {
                "id": "999",
                "account_id": "456",
                "configured_status": "PAUSED",
            }
        }

    monkeypatch.setattr(real_provider, "_get_json", fake_get_json)
    with pytest.raises(MetaAdsProviderError, match="mismatched Campaign"):
        await real_provider.get_campaign_state("token", "act_456", "123")


@pytest.mark.asyncio
async def test_real_provider_rejects_incomplete_ad_set_payload(real_provider, monkeypatch):
    async def fake_get_json(*args, **kwargs):
        return {"id": "789", "account_id": "456", "status": "PAUSED"}

    monkeypatch.setattr(real_provider, "_get_json", fake_get_json)
    with pytest.raises(MetaAdsProviderError, match="Ad Set campaign"):
        await real_provider.get_ad_set_state("token", "act_456", "123", "789")
