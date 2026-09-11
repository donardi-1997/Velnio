from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meta_ads import MetaAdsAdSetPublication, MetaAdsCampaignPublication, MetaAdsConnection
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError


async def _register(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "Test12345!", "first_name": "Meta", "last_name": "AdSet"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _setup(client: AsyncClient, token: str, *, configure: bool = True) -> tuple[str, dict]:
    headers = _headers(token)
    campaign = await client.post(
        "/api/campaigns",
        headers=headers,
        json={"name": "Meta Ad Set launch", "target_country": "CO", "currency": "COP"},
    )
    assert campaign.status_code == 201
    campaign_id = campaign.json()["id"]
    assert (await client.post("/api/meta-ads/connect-mock", headers=headers)).status_code == 200
    publication = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publish",
        headers=headers,
        json={"ad_account_id": "act_1000000001"},
    )
    assert publication.status_code == 200
    pub = publication.json()
    if configure:
        configured = await client.patch(
            f"/api/campaigns/{campaign_id}/meta-ads/publications/{pub['id']}/delivery-config",
            headers=headers,
            json={
                "pixel_id": "1000000001501",
                "page_id": "1000000001601",
                "instagram_account_id": "1000000001701",
            },
        )
        assert configured.status_code == 200
    return campaign_id, pub


def _path(campaign_id: str, publication_id: str) -> str:
    return f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication_id}/ad-set"


@pytest.mark.asyncio
async def test_meta_ad_set_get_returns_null_before_creation(client: AsyncClient):
    token = await _register(client, "meta-adset-empty@test.com")
    campaign_id, pub = await _setup(client, token)
    response = await client.get(_path(campaign_id, pub["id"]), headers=_headers(token))
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_meta_ad_set_publish_is_paused_and_uses_account_currency(client: AsyncClient):
    token = await _register(client, "meta-adset-create@test.com")
    campaign_id, pub = await _setup(client, token)
    response = await client.post(
        _path(campaign_id, pub["id"]), headers=_headers(token), json={"daily_budget_minor": 2500}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["remote_status"] == "PAUSED"
    assert payload["daily_budget_minor"] == 2500
    assert payload["target_country"] == "CO"
    assert payload["currency"] == "USD"  # account currency, not Campaign.currency (COP)
    assert payload["optimization_goal"] == "OFFSITE_CONVERSIONS"
    assert payload["billing_event"] == "IMPRESSIONS"
    assert payload["bid_strategy"] == "LOWEST_COST_WITHOUT_CAP"
    assert payload["reused"] is False


@pytest.mark.asyncio
async def test_meta_ad_set_country_override_is_normalized(client: AsyncClient):
    token = await _register(client, "meta-adset-country@test.com")
    campaign_id, pub = await _setup(client, token)
    response = await client.post(
        _path(campaign_id, pub["id"]),
        headers=_headers(token),
        json={"daily_budget_minor": 2500, "target_country": "mx"},
    )
    assert response.status_code == 200
    assert response.json()["target_country"] == "MX"


@pytest.mark.asyncio
async def test_meta_ad_set_repeat_is_idempotent(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-adset-idempotent@test.com")
    campaign_id, pub = await _setup(client, token)
    path = _path(campaign_id, pub["id"])
    first = await client.post(path, headers=_headers(token), json={"daily_budget_minor": 3000})
    second = await client.post(path, headers=_headers(token), json={"daily_budget_minor": 3000})
    assert first.status_code == second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["remote_ad_set_id"] == first.json()["remote_ad_set_id"]
    assert second.json()["reused"] is True
    result = await db_session.execute(
        select(MetaAdsAdSetPublication).where(
            MetaAdsAdSetPublication.campaign_publication_id == UUID(pub["id"])
        )
    )
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_meta_ad_set_rejects_changed_budget(client: AsyncClient):
    token = await _register(client, "meta-adset-budget@test.com")
    campaign_id, pub = await _setup(client, token)
    path = _path(campaign_id, pub["id"])
    assert (await client.post(path, headers=_headers(token), json={"daily_budget_minor": 2500})).status_code == 200
    response = await client.post(path, headers=_headers(token), json={"daily_budget_minor": 9999})
    assert response.status_code == 400
    assert "different immutable settings" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ad_set_requires_delivery_config(client: AsyncClient):
    token = await _register(client, "meta-adset-config@test.com")
    campaign_id, pub = await _setup(client, token, configure=False)
    response = await client.post(
        _path(campaign_id, pub["id"]), headers=_headers(token), json={"daily_budget_minor": 2500}
    )
    assert response.status_code == 400
    assert "configure" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ad_set_revalidates_pixel(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-adset-pixel@test.com")
    campaign_id, pub = await _setup(client, token)
    result = await db_session.execute(
        select(MetaAdsCampaignPublication).where(MetaAdsCampaignPublication.id == UUID(pub["id"]))
    )
    row = result.scalar_one()
    row.pixel_id = "999999"
    await db_session.commit()
    response = await client.post(
        _path(campaign_id, pub["id"]), headers=_headers(token), json={"daily_budget_minor": 2500}
    )
    assert response.status_code == 403
    assert "pixel" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ad_set_refuses_non_paused_campaign(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-adset-active@test.com")
    campaign_id, pub = await _setup(client, token)
    result = await db_session.execute(
        select(MetaAdsCampaignPublication).where(MetaAdsCampaignPublication.id == UUID(pub["id"]))
    )
    row = result.scalar_one()
    row.remote_status = "ACTIVE"
    await db_session.commit()
    response = await client.post(
        _path(campaign_id, pub["id"]), headers=_headers(token), json={"daily_budget_minor": 2500}
    )
    assert response.status_code == 403
    assert "paused" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ad_set_requires_management_scope(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-adset-scope@test.com")
    campaign_id, pub = await _setup(client, token)
    result = await db_session.execute(select(MetaAdsConnection).where(MetaAdsConnection.is_active == True))
    connection = result.scalar_one()
    connection.scopes = "ads_read"
    await db_session.commit()
    response = await client.post(
        _path(campaign_id, pub["id"]), headers=_headers(token), json={"daily_budget_minor": 2500}
    )
    assert response.status_code == 403
    assert "ads_management" in response.json()["detail"]


@pytest.mark.asyncio
async def test_meta_ad_set_is_workspace_isolated(client: AsyncClient):
    owner = await _register(client, "meta-adset-owner@test.com")
    other = await _register(client, "meta-adset-other@test.com")
    campaign_id, pub = await _setup(client, owner)
    await client.post("/api/meta-ads/connect-mock", headers=_headers(other))
    response = await client.post(
        _path(campaign_id, pub["id"]), headers=_headers(other), json={"daily_budget_minor": 2500}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_meta_ad_set_provider_failure_is_sanitized(client: AsyncClient, monkeypatch):
    token = await _register(client, "meta-adset-provider@test.com")
    campaign_id, pub = await _setup(client, token)

    class FailingProvider:
        async def ensure_paused_ad_set(self, *args, **kwargs):
            raise MetaAdsProviderError("upstream-private-detail")

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_adsets.get_meta_ads_provider",
        lambda: FailingProvider(),
    )
    response = await client.post(
        _path(campaign_id, pub["id"]), headers=_headers(token), json={"daily_budget_minor": 2500}
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "Meta Ads Ad Set creation failed"
    assert "upstream-private-detail" not in response.text
