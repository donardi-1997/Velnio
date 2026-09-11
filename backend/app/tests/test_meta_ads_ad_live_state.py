import hashlib
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meta_ads import MetaAdsCampaignPublication, MetaAdsConnection, MetaAdsCreativePublication
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError


async def _register(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "Test12345!", "first_name": "Meta", "last_name": "State"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _setup(client: AsyncClient, db_session: AsyncSession, token: str) -> tuple[str, dict, dict]:
    headers = _headers(token)
    campaign_response = await client.post(
        "/api/campaigns",
        headers=headers,
        json={"name": "Meta live state", "target_country": "CO", "currency": "COP"},
    )
    assert campaign_response.status_code == 201
    campaign_id = campaign_response.json()["id"]

    assert (await client.post("/api/meta-ads/connect-mock", headers=headers)).status_code == 200
    publication_response = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publish",
        headers=headers,
        json={"ad_account_id": "act_1000000001"},
    )
    assert publication_response.status_code == 200
    publication = publication_response.json()

    configured = await client.patch(
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication['id']}/delivery-config",
        headers=headers,
        json={
            "pixel_id": "1000000001501",
            "page_id": "1000000001601",
            "instagram_account_id": "1000000001701",
        },
    )
    assert configured.status_code == 200

    ad_set_response = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication['id']}/ad-set",
        headers=headers,
        json={"daily_budget_minor": 2500},
    )
    assert ad_set_response.status_code == 200
    ad_set = ad_set_response.json()

    result = await db_session.execute(
        select(MetaAdsCampaignPublication).where(
            MetaAdsCampaignPublication.id == UUID(publication["id"])
        )
    )
    publication_row = result.scalar_one()
    fingerprint = hashlib.sha256(f"live-state:{publication['id']}:{ad_set['id']}".encode()).hexdigest()
    creative = MetaAdsCreativePublication(
        workspace_id=publication_row.workspace_id,
        campaign_publication_id=publication_row.id,
        ad_set_publication_id=UUID(ad_set["id"]),
        product_image_id=None,
        created_by_user_id=publication_row.created_by_user_id,
        idempotency_key=fingerprint,
        remote_creative_id="mock_meta_creative_live_state",
        remote_creative_name="Live state creative",
        destination_url="https://velnio-test.myshopify.com/pages/live-state",
        image_url="https://cdn.example.test/live-state.jpg",
        primary_text="Live state creative",
        headline="Live state",
        call_to_action="SHOP_NOW",
        page_id=publication_row.page_id or "1000000001601",
        instagram_account_id=publication_row.instagram_account_id,
    )
    db_session.add(creative)
    await db_session.commit()
    await db_session.refresh(creative)

    ad_response = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication['id']}/ads",
        headers=headers,
        json={"creative_publication_id": str(creative.id)},
    )
    assert ad_response.status_code == 200
    return campaign_id, publication, ad_response.json()


def _state_path(campaign_id: str, publication_id: str, ad_id: str) -> str:
    return (
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication_id}"
        f"/ads/{ad_id}/remote-state"
    )


@pytest.mark.asyncio
async def test_meta_ad_remote_state_returns_validated_live_status(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-live-state@test.com")
    campaign_id, publication, ad = await _setup(client, db_session, token)

    response = await client.get(
        _state_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ad_publication_id"] == ad["id"]
    assert payload["remote_ad_id"] == ad["remote_ad_id"]
    assert payload["configured_status"] == "PAUSED"
    assert payload["effective_status"] == "PAUSED"
    assert payload["account_id"] == "1000000001"


@pytest.mark.asyncio
async def test_meta_ad_remote_state_is_read_only_and_does_not_require_management_scope(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-live-read@test.com")
    campaign_id, publication, ad = await _setup(client, db_session, token)
    result = await db_session.execute(select(MetaAdsConnection).where(MetaAdsConnection.is_active == True))
    connection = result.scalar_one()
    connection.scopes = "ads_read"
    await db_session.commit()

    response = await client.get(
        _state_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["configured_status"] == "PAUSED"


@pytest.mark.asyncio
async def test_meta_ad_remote_state_is_workspace_isolated(client: AsyncClient, db_session: AsyncSession):
    owner = await _register(client, "meta-live-owner@test.com")
    other = await _register(client, "meta-live-other@test.com")
    campaign_id, publication, ad = await _setup(client, db_session, owner)

    response = await client.get(
        _state_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(other),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_meta_ad_remote_state_rejects_remote_relationship_mismatch(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
):
    token = await _register(client, "meta-live-mismatch@test.com")
    campaign_id, publication, ad = await _setup(client, db_session, token)

    class MismatchedProvider:
        async def get_ad_state(self, access_token, ad_account_id, campaign_id, adset_id, creative_id, ad_id):
            return {
                "id": ad_id,
                "account_id": ad_account_id.removeprefix("act_"),
                "campaign_id": campaign_id,
                "adset_id": adset_id,
                "creative_id": "different-creative",
                "status": "PAUSED",
                "effective_status": "PAUSED",
            }

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_remote_state.get_meta_ads_status_provider",
        lambda: MismatchedProvider(),
    )
    response = await client.get(
        _state_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert response.status_code == 403
    assert "adcreative" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ad_remote_state_provider_failure_is_sanitized(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
):
    token = await _register(client, "meta-live-provider@test.com")
    campaign_id, publication, ad = await _setup(client, db_session, token)

    class FailingProvider:
        async def get_ad_state(self, *args, **kwargs):
            raise MetaAdsProviderError("private-upstream-body")

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_remote_state.get_meta_ads_status_provider",
        lambda: FailingProvider(),
    )
    response = await client.get(
        _state_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "Could not verify current Meta Ad state"
    assert "private-upstream-body" not in response.text
