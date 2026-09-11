import pytest

from app.core.config import settings
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError
from app.modules.integrations.infrastructure.meta_ads_activation import RealMetaAdsActivationProvider


class FakeStatusProvider:
    def __init__(self) -> None:
        self.campaign_status = "PAUSED"
        self.ad_set_status = "PAUSED"
        self.ad_status = "PAUSED"

    async def get_campaign_state(self, access_token, ad_account_id, campaign_id):
        return {
            "id": campaign_id,
            "account_id": ad_account_id.removeprefix("act_"),
            "status": self.campaign_status,
            "effective_status": self.campaign_status,
        }

    async def get_ad_set_state(self, access_token, ad_account_id, campaign_id, ad_set_id):
        return {
            "id": ad_set_id,
            "account_id": ad_account_id.removeprefix("act_"),
            "campaign_id": campaign_id,
            "status": self.ad_set_status,
            "effective_status": self.ad_set_status,
        }

    async def get_ad_state(
        self,
        access_token,
        ad_account_id,
        campaign_id,
        ad_set_id,
        creative_id,
        ad_id,
    ):
        return {
            "id": ad_id,
            "account_id": ad_account_id.removeprefix("act_"),
            "campaign_id": campaign_id,
            "adset_id": ad_set_id,
            "creative_id": creative_id,
            "status": self.ad_status,
            "effective_status": self.ad_status,
        }


@pytest.fixture
def real_provider(monkeypatch):
    monkeypatch.setattr(settings, "META_APP_ID", "test-app-id")
    monkeypatch.setattr(settings, "META_APP_SECRET", "test-app-secret")
    monkeypatch.setattr(settings, "META_REDIRECT_URI", "https://example.test/meta/callback")
    provider = RealMetaAdsActivationProvider()
    provider.status_provider = FakeStatusProvider()
    return provider


@pytest.mark.asyncio
async def test_real_activation_provider_transitions_ad_with_minimal_payload_and_verification(
    real_provider,
    monkeypatch,
):
    captured = []

    async def fake_post_json(url, *, data):
        captured.append((url, data.copy()))
        real_provider.status_provider.ad_status = data["status"]
        return {"success": True}

    monkeypatch.setattr(real_provider, "_post_json", fake_post_json)
    state = await real_provider.set_ad_status(
        "token",
        "act_1001",
        "111",
        "222",
        "333",
        "444",
        "ACTIVE",
        expected_status="PAUSED",
    )

    assert state["status"] == "ACTIVE"
    assert len(captured) == 1
    assert captured[0][0].endswith("/444")
    assert captured[0][1] == {"access_token": "token", "status": "ACTIVE"}


@pytest.mark.asyncio
async def test_real_activation_provider_rejects_unexpected_already_active_resource(
    real_provider,
    monkeypatch,
):
    real_provider.status_provider.ad_status = "ACTIVE"

    async def fail_post(*args, **kwargs):
        raise AssertionError("POST must not run when the launch baseline changed")

    monkeypatch.setattr(real_provider, "_post_json", fail_post)
    with pytest.raises(MetaAdsProviderError, match="already ACTIVE"):
        await real_provider.set_ad_status(
            "token",
            "act_1001",
            "111",
            "222",
            "333",
            "444",
            "ACTIVE",
            expected_status="PAUSED",
        )


@pytest.mark.asyncio
async def test_real_activation_provider_pause_is_idempotent(real_provider, monkeypatch):
    real_provider.status_provider.campaign_status = "PAUSED"

    async def fail_post(*args, **kwargs):
        raise AssertionError("POST must not run when rollback target is already PAUSED")

    monkeypatch.setattr(real_provider, "_post_json", fail_post)
    state = await real_provider.set_campaign_status(
        "token",
        "act_1001",
        "111",
        "PAUSED",
    )
    assert state["status"] == "PAUSED"


@pytest.mark.asyncio
async def test_real_activation_provider_rejects_relationship_mismatch_before_write(
    real_provider,
    monkeypatch,
):
    async def mismatched_ad(*args, **kwargs):
        return {
            "id": "444",
            "account_id": "1001",
            "campaign_id": "999",
            "adset_id": "222",
            "creative_id": "333",
            "status": "PAUSED",
            "effective_status": "PAUSED",
        }

    real_provider.status_provider.get_ad_state = mismatched_ad

    async def fail_post(*args, **kwargs):
        raise AssertionError("POST must not run for mismatched remote relationships")

    monkeypatch.setattr(real_provider, "_post_json", fail_post)
    with pytest.raises(MetaAdsProviderError, match="different Campaign"):
        await real_provider.set_ad_status(
            "token",
            "act_1001",
            "111",
            "222",
            "333",
            "444",
            "ACTIVE",
            expected_status="PAUSED",
        )
