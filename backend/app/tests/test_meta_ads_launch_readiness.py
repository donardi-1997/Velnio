import hashlib
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException
from app.models.campaign import Campaign, CampaignStatus
from app.models.meta_ads import (
    MetaAdsAdSetPublication,
    MetaAdsCampaignPublication,
    MetaAdsConnection,
    MetaAdsCreativePublication,
    MetaAdsLaunchIntent,
)
from app.models.store import Store, StoreStatus
from app.modules.campaigns.application.meta_ads_launch_intents import MetaAdsLaunchIntentService


async def _register(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "Test12345!", "first_name": "Meta", "last_name": "Ready"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _path(campaign_id: str, publication_id: str, ad_id: str) -> str:
    return (
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication_id}"
        f"/ads/{ad_id}/launch-readiness"
    )


def _intent_path(campaign_id: str, publication_id: str, ad_id: str) -> str:
    return (
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication_id}"
        f"/ads/{ad_id}/launch-intent"
    )


async def _setup_ready(
    client: AsyncClient,
    db_session: AsyncSession,
    token: str,
) -> tuple[str, dict, dict, MetaAdsCreativePublication]:
    headers = _headers(token)
    campaign_response = await client.post(
        "/api/campaigns",
        headers=headers,
        json={"name": "Launch readiness", "target_country": "CO", "currency": "COP"},
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

    campaign_result = await db_session.execute(select(Campaign).where(Campaign.id == UUID(campaign_id)))
    campaign = campaign_result.scalar_one()
    store = Store(
        workspace_id=campaign.workspace_id,
        name="Readiness Store",
        shop_domain="velnio-readiness.myshopify.com",
        status=StoreStatus.CONNECTED,
        country="CO",
        currency="COP",
    )
    db_session.add(store)
    await db_session.flush()
    campaign.store_id = store.id
    campaign.status = CampaignStatus.PUBLISHED
    campaign.external_page_id = "gid://shopify/Page/999"
    campaign.external_page_handle = "launch-readiness"
    campaign.external_page_url = "https://velnio-readiness.myshopify.com/pages/launch-readiness"

    publication_result = await db_session.execute(
        select(MetaAdsCampaignPublication).where(
            MetaAdsCampaignPublication.id == UUID(publication["id"])
        )
    )
    publication_row = publication_result.scalar_one()
    fingerprint = hashlib.sha256(f"readiness:{publication['id']}:{ad_set['id']}".encode()).hexdigest()
    creative = MetaAdsCreativePublication(
        workspace_id=publication_row.workspace_id,
        campaign_publication_id=publication_row.id,
        ad_set_publication_id=UUID(ad_set["id"]),
        product_image_id=None,
        created_by_user_id=publication_row.created_by_user_id,
        idempotency_key=fingerprint,
        remote_creative_id="mock_meta_creative_readiness",
        remote_creative_name="Readiness creative",
        destination_url=campaign.external_page_url,
        image_url="https://cdn.example.test/readiness.jpg",
        primary_text="Readiness copy",
        headline="Ready to launch",
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
    return campaign_id, publication, ad_response.json(), creative


def _checks(payload: dict) -> dict[str, dict]:
    return {item["key"]: item for item in payload["checks"]}


@pytest.mark.asyncio
async def test_meta_launch_readiness_happy_path_is_read_only(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-readiness-ok@test.com")
    campaign_id, publication, ad, creative = await _setup_ready(client, db_session, token)

    response = await client.get(
        _path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["side_effects_performed"] is False
    assert len(payload["readiness_fingerprint"]) == 64
    assert all(item["status"] == "PASS" for item in payload["checks"])
    plan = payload["launch_plan"]
    assert plan["remote_campaign_id"] == publication["remote_campaign_id"]
    assert plan["remote_ad_id"] == ad["remote_ad_id"]
    assert plan["remote_creative_id"] == creative.remote_creative_id
    assert plan["daily_budget_minor"] == 2500
    assert plan["currency"] == "USD"
    assert plan["target_country"] == "CO"
    assert plan["current_configured_statuses"] == {
        "campaign": "PAUSED",
        "ad_set": "PAUSED",
        "ad": "PAUSED",
    }
    assert plan["proposed_statuses"] == {
        "campaign": "ACTIVE",
        "ad_set": "ACTIVE",
        "ad": "ACTIVE",
    }


@pytest.mark.asyncio
async def test_meta_launch_readiness_reports_missing_management_scope_without_error(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-readiness-scope@test.com")
    campaign_id, publication, ad, _ = await _setup_ready(client, db_session, token)
    result = await db_session.execute(select(MetaAdsConnection).where(MetaAdsConnection.is_active == True))
    connection = result.scalar_one()
    connection.scopes = "ads_read"
    await db_session.commit()

    response = await client.get(
        _path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is False
    assert _checks(payload)["ads_management_scope"]["status"] == "FAIL"
    assert payload["side_effects_performed"] is False


@pytest.mark.asyncio
async def test_meta_launch_readiness_detects_changed_shopify_destination(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-readiness-destination@test.com")
    campaign_id, publication, ad, _ = await _setup_ready(client, db_session, token)
    result = await db_session.execute(select(Campaign).where(Campaign.id == UUID(campaign_id)))
    campaign = result.scalar_one()
    campaign.external_page_url = "https://velnio-readiness.myshopify.com/pages/new-landing"
    await db_session.commit()

    response = await client.get(
        _path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is False
    assert _checks(payload)["creative_destination"]["status"] == "FAIL"


@pytest.mark.asyncio
async def test_meta_launch_readiness_detects_stale_delivery_resource(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-readiness-resource@test.com")
    campaign_id, publication, ad, _ = await _setup_ready(client, db_session, token)
    result = await db_session.execute(
        select(MetaAdsCampaignPublication).where(
            MetaAdsCampaignPublication.id == UUID(publication["id"])
        )
    )
    row = result.scalar_one()
    row.page_id = "999999"
    await db_session.commit()

    response = await client.get(
        _path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is False
    assert _checks(payload)["delivery_resources_live"]["status"] == "FAIL"


@pytest.mark.asyncio
async def test_meta_launch_readiness_reports_remote_active_ad_as_not_ready(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
):
    token = await _register(client, "meta-readiness-active@test.com")
    campaign_id, publication, ad, _ = await _setup_ready(client, db_session, token)

    async def refuse(*args, **kwargs):
        raise ForbiddenException("Remote Meta Ad must be PAUSED before continuing")

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_launch_readiness.MetaAdsRemoteStateGuard.require_paused_full_hierarchy",
        refuse,
    )
    response = await client.get(
        _path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is False
    assert _checks(payload)["remote_paused_hierarchy"]["status"] == "FAIL"
    assert "PAUSED" in _checks(payload)["remote_paused_hierarchy"]["message"]


@pytest.mark.asyncio
async def test_meta_launch_readiness_is_workspace_isolated(
    client: AsyncClient,
    db_session: AsyncSession,
):
    owner = await _register(client, "meta-readiness-owner@test.com")
    other = await _register(client, "meta-readiness-other@test.com")
    campaign_id, publication, ad, _ = await _setup_ready(client, db_session, owner)

    response = await client.get(
        _path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(other),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_meta_launch_readiness_fingerprint_changes_when_budget_changes(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-readiness-fingerprint@test.com")
    campaign_id, publication, ad, _ = await _setup_ready(client, db_session, token)
    first = await client.get(
        _path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert first.status_code == 200
    assert first.json()["ready"] is True

    result = await db_session.execute(
        select(MetaAdsAdSetPublication).where(
            MetaAdsAdSetPublication.id == UUID(ad["ad_set_publication_id"])
        )
    )
    ad_set = result.scalar_one()
    ad_set.daily_budget_minor = 3500
    await db_session.commit()

    second = await client.get(
        _path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert second.status_code == 200
    assert second.json()["ready"] is True
    assert first.json()["readiness_fingerprint"] != second.json()["readiness_fingerprint"]


@pytest.mark.asyncio
async def test_meta_launch_intent_stores_only_token_hash_and_expires_shortly(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-launch-intent@test.com")
    campaign_id, publication, ad, _ = await _setup_ready(client, db_session, token)
    readiness = await client.get(
        _path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert readiness.status_code == 200

    response = await client.post(
        _intent_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "PENDING_CONFIRMATION"
    assert payload["side_effects_performed"] is False
    assert payload["readiness_fingerprint"] == readiness.json()["readiness_fingerprint"]
    assert len(payload["confirmation_token"]) >= 32

    result = await db_session.execute(
        select(MetaAdsLaunchIntent).where(MetaAdsLaunchIntent.id == UUID(payload["id"]))
    )
    row = result.scalar_one()
    assert row.token_hash != payload["confirmation_token"]
    assert row.token_hash == MetaAdsLaunchIntentService.hash_token(payload["confirmation_token"])
    assert row.consumed_at is None
    lifetime_seconds = (row.expires_at - row.created_at).total_seconds()
    assert 540 <= lifetime_seconds <= 660


@pytest.mark.asyncio
async def test_meta_launch_intent_invalidates_previous_for_same_user_and_ad(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-launch-intent-replace@test.com")
    campaign_id, publication, ad, _ = await _setup_ready(client, db_session, token)
    path = _intent_path(campaign_id, publication["id"], ad["id"])

    first = await client.post(path, headers=_headers(token))
    second = await client.post(path, headers=_headers(token))
    assert first.status_code == second.status_code == 200
    assert first.json()["confirmation_token"] != second.json()["confirmation_token"]

    result = await db_session.execute(
        select(MetaAdsLaunchIntent)
        .where(MetaAdsLaunchIntent.ad_publication_id == UUID(ad["id"]))
        .order_by(MetaAdsLaunchIntent.created_at.asc())
    )
    rows = result.scalars().all()
    assert len(rows) == 2
    assert rows[0].consumed_at is not None
    assert rows[1].consumed_at is None


@pytest.mark.asyncio
async def test_meta_launch_intent_refuses_when_readiness_fails(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-launch-intent-not-ready@test.com")
    campaign_id, publication, ad, _ = await _setup_ready(client, db_session, token)
    result = await db_session.execute(select(MetaAdsConnection).where(MetaAdsConnection.is_active == True))
    connection = result.scalar_one()
    connection.scopes = "ads_read"
    await db_session.commit()

    response = await client.post(
        _intent_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert response.status_code == 400
    assert "readiness" in response.json()["detail"].lower()

    rows = await db_session.execute(select(MetaAdsLaunchIntent))
    assert rows.scalars().all() == []


@pytest.mark.asyncio
async def test_meta_launch_intent_is_workspace_isolated(
    client: AsyncClient,
    db_session: AsyncSession,
):
    owner = await _register(client, "meta-launch-intent-owner@test.com")
    other = await _register(client, "meta-launch-intent-other@test.com")
    campaign_id, publication, ad, _ = await _setup_ready(client, db_session, owner)

    response = await client.post(
        _intent_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(other),
    )
    assert response.status_code == 404
