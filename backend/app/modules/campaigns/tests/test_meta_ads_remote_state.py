from types import SimpleNamespace

import pytest

from app.core.exceptions import BadGatewayException, ForbiddenException
from app.modules.campaigns.application.meta_ads_remote_state import MetaAdsRemoteStateGuard
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError


@pytest.fixture
def publication():
    return SimpleNamespace(
        ad_account_id="act_456",
        remote_campaign_id="123",
    )


@pytest.fixture
def ad_set():
    return SimpleNamespace(remote_ad_set_id="789")


@pytest.fixture
def creative():
    return SimpleNamespace(remote_creative_id="333")


@pytest.fixture
def ad():
    return SimpleNamespace(remote_ad_id="444")


@pytest.mark.asyncio
async def test_remote_guard_accepts_exact_paused_hierarchy(monkeypatch, publication, ad_set):
    class Provider:
        async def get_campaign_state(self, *args):
            return {"id": "123", "account_id": "456", "status": "PAUSED", "effective_status": "PAUSED"}

        async def get_ad_set_state(self, *args):
            return {
                "id": "789",
                "account_id": "456",
                "campaign_id": "123",
                "status": "PAUSED",
                "effective_status": "PAUSED",
            }

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_remote_state.get_meta_ads_status_provider",
        lambda: Provider(),
    )
    result = await MetaAdsRemoteStateGuard().require_paused_hierarchy("token", publication, ad_set)
    assert result["campaign"]["status"] == "PAUSED"
    assert result["ad_set"]["status"] == "PAUSED"


@pytest.mark.asyncio
async def test_remote_guard_blocks_campaign_activated_outside_velnio(monkeypatch, publication):
    class Provider:
        async def get_campaign_state(self, *args):
            return {"id": "123", "account_id": "456", "status": "ACTIVE", "effective_status": "ACTIVE"}

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_remote_state.get_meta_ads_status_provider",
        lambda: Provider(),
    )
    with pytest.raises(ForbiddenException, match="Campaign must be PAUSED"):
        await MetaAdsRemoteStateGuard().require_paused_campaign("token", publication)


@pytest.mark.asyncio
async def test_remote_guard_blocks_ad_set_activated_outside_velnio(monkeypatch, publication, ad_set):
    class Provider:
        async def get_campaign_state(self, *args):
            return {"id": "123", "account_id": "456", "status": "PAUSED"}

        async def get_ad_set_state(self, *args):
            return {"id": "789", "account_id": "456", "campaign_id": "123", "status": "ACTIVE"}

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_remote_state.get_meta_ads_status_provider",
        lambda: Provider(),
    )
    with pytest.raises(ForbiddenException, match="Ad Set must be PAUSED"):
        await MetaAdsRemoteStateGuard().require_paused_hierarchy("token", publication, ad_set)


@pytest.mark.asyncio
async def test_remote_guard_blocks_ad_activated_outside_velnio(
    monkeypatch,
    publication,
    ad_set,
    creative,
    ad,
):
    class Provider:
        async def get_campaign_state(self, *args):
            return {"id": "123", "account_id": "456", "status": "PAUSED"}

        async def get_ad_set_state(self, *args):
            return {"id": "789", "account_id": "456", "campaign_id": "123", "status": "PAUSED"}

        async def get_ad_state(self, *args):
            return {
                "id": "444",
                "account_id": "456",
                "campaign_id": "123",
                "adset_id": "789",
                "creative_id": "333",
                "status": "ACTIVE",
                "effective_status": "CAMPAIGN_PAUSED",
            }

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_remote_state.get_meta_ads_status_provider",
        lambda: Provider(),
    )
    with pytest.raises(ForbiddenException, match="Ad must be PAUSED"):
        await MetaAdsRemoteStateGuard().require_paused_full_hierarchy(
            "token",
            publication,
            ad_set,
            creative,
            ad,
        )


@pytest.mark.asyncio
async def test_remote_guard_blocks_campaign_account_mismatch(monkeypatch, publication):
    class Provider:
        async def get_campaign_state(self, *args):
            return {"id": "123", "account_id": "999", "status": "PAUSED"}

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_remote_state.get_meta_ads_status_provider",
        lambda: Provider(),
    )
    with pytest.raises(ForbiddenException, match="configured ad account"):
        await MetaAdsRemoteStateGuard().require_paused_campaign("token", publication)


@pytest.mark.asyncio
async def test_remote_guard_blocks_ad_set_campaign_mismatch(monkeypatch, publication, ad_set):
    class Provider:
        async def get_campaign_state(self, *args):
            return {"id": "123", "account_id": "456", "status": "PAUSED"}

        async def get_ad_set_state(self, *args):
            return {"id": "789", "account_id": "456", "campaign_id": "999", "status": "PAUSED"}

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_remote_state.get_meta_ads_status_provider",
        lambda: Provider(),
    )
    with pytest.raises(ForbiddenException, match="expected Campaign"):
        await MetaAdsRemoteStateGuard().require_paused_hierarchy("token", publication, ad_set)


@pytest.mark.asyncio
async def test_remote_guard_sanitizes_provider_failures(monkeypatch, publication):
    class Provider:
        async def get_campaign_state(self, *args):
            raise MetaAdsProviderError("private-upstream-detail")

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_remote_state.get_meta_ads_status_provider",
        lambda: Provider(),
    )
    with pytest.raises(BadGatewayException) as exc_info:
        await MetaAdsRemoteStateGuard().require_paused_campaign("token", publication)
    assert exc_info.value.detail == "Could not verify current Meta Campaign state"
    assert "private-upstream-detail" not in exc_info.value.detail
