import hashlib
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException
from app.models.meta_ads import (
    MetaAdsAdPublication,
    MetaAdsAdSetPublication,
    MetaAdsCampaignPublication,
    MetaAdsConnection,
    MetaAdsCreativePublication,
)
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError


async def _register(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "Test12345!", "first_name": "Meta", "last_name": "Ad"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _ads_path(campaign_id: str, publication_id: str) -> str:
    return f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication_id}/ads"


async def _setup_ad_set(client: AsyncClient, token: str) -> tuple[str, dict, dict]:
    headers = _headers(token)
    campaign = await client.post(
        "/api/campaigns",
        headers=headers,
        json={"name": "Meta paused Ad", "target_country": "CO", "currency": "COP"},
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
    ad_set = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{pub['id']}/ad-set",
        headers=headers,
        json={"daily_budget_minor": 2500},
    )
    assert ad_set.status_code == 200
    return campaign_id, pub, ad_set.json()


async def _create_creative_record(
    db_session: AsyncSession,
    publication_id: str,
    ad_set_id: str,
    *,
    suffix: str,
) -> MetaAdsCreativePublication:
    result = await db_session.execute(
        select(MetaAdsCampaignPublication).where(MetaAdsCampaignPublication.id == UUID(publication_id))
    )
    publication = result.scalar_one()
    fingerprint = hashlib.sha256(f"creative:{suffix}:{publication_id}:{ad_set_id}".encode()).hexdigest()
    row = MetaAdsCreativePublication(
        workspace_id=publication.workspace_id,
        campaign_publication_id=publication.id,
        ad_set_publication_id=UUID(ad_set_id),
        product_image_id=None,
        created_by_user_id=publication.created_by_user_id,
        idempotency_key=fingerprint,
        remote_creative_id=f"mock_meta_creative_manual_{suffix}",
        remote_creative_name=f"Creative {suffix}",
        destination_url="https://velnio-test.myshopify.com/pages/launch",
        image_url="https://cdn.example.test/meta.jpg",
        primary_text=f"Creative {suffix}",
        headline="Launch",
        call_to_action="SHOP_NOW",
        page_id=publication.page_id or "1000000001601",
        instagram_account_id=publication.instagram_account_id,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


@pytest.mark.asyncio
async def test_meta_ad_list_empty_before_creation(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-ad-empty@test.com")
    campaign_id, pub, _ = await _setup_ad_set(client, token)
    response = await client.get(_ads_path(campaign_id, pub["id"]), headers=_headers(token))
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_meta_ad_is_created_paused_from_existing_adset_and_creative(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-ad-create@test.com")
    campaign_id, pub, ad_set = await _setup_ad_set(client, token)
    creative = await _create_creative_record(db_session, pub["id"], ad_set["id"], suffix="create")

    response = await client.post(
        _ads_path(campaign_id, pub["id"]),
        headers=_headers(token),
        json={"creative_publication_id": str(creative.id)},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["remote_status"] == "PAUSED"
    assert payload["campaign_publication_id"] == pub["id"]
    assert payload["ad_set_publication_id"] == ad_set["id"]
    assert payload["creative_publication_id"] == str(creative.id)
    assert payload["remote_ad_id"].startswith("mock_meta_ad_")
    assert payload["reused"] is False


@pytest.mark.asyncio
async def test_meta_ad_retry_is_idempotent(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-ad-idempotent@test.com")
    campaign_id, pub, ad_set = await _setup_ad_set(client, token)
    creative = await _create_creative_record(db_session, pub["id"], ad_set["id"], suffix="idem")
    path = _ads_path(campaign_id, pub["id"])
    body = {"creative_publication_id": str(creative.id)}

    first = await client.post(path, headers=_headers(token), json=body)
    second = await client.post(path, headers=_headers(token), json=body)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["remote_ad_id"] == second.json()["remote_ad_id"]
    assert second.json()["reused"] is True

    result = await db_session.execute(
        select(MetaAdsAdPublication).where(
            MetaAdsAdPublication.campaign_publication_id == UUID(pub["id"])
        )
    )
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_meta_ad_allows_one_paused_ad_per_distinct_creative(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-ad-variants@test.com")
    campaign_id, pub, ad_set = await _setup_ad_set(client, token)
    creative_a = await _create_creative_record(db_session, pub["id"], ad_set["id"], suffix="a")
    creative_b = await _create_creative_record(db_session, pub["id"], ad_set["id"], suffix="b")
    path = _ads_path(campaign_id, pub["id"])

    first = await client.post(path, headers=_headers(token), json={"creative_publication_id": str(creative_a.id)})
    second = await client.post(path, headers=_headers(token), json={"creative_publication_id": str(creative_b.id)})
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] != second.json()["id"]
    listed = await client.get(path, headers=_headers(token))
    assert listed.status_code == 200
    assert len(listed.json()) == 2


@pytest.mark.asyncio
async def test_meta_ad_rejects_creative_from_other_publication(client: AsyncClient, db_session: AsyncSession):
    owner = await _register(client, "meta-ad-owner@test.com")
    other = await _register(client, "meta-ad-other@test.com")
    campaign_id, pub, _ = await _setup_ad_set(client, owner)
    _, other_pub, other_ad_set = await _setup_ad_set(client, other)
    other_creative = await _create_creative_record(
        db_session, other_pub["id"], other_ad_set["id"], suffix="other"
    )

    response = await client.post(
        _ads_path(campaign_id, pub["id"]),
        headers=_headers(owner),
        json={"creative_publication_id": str(other_creative.id)},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_meta_ad_refuses_non_paused_local_ad_set(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-ad-active-local@test.com")
    campaign_id, pub, ad_set_payload = await _setup_ad_set(client, token)
    creative = await _create_creative_record(db_session, pub["id"], ad_set_payload["id"], suffix="active")
    result = await db_session.execute(
        select(MetaAdsAdSetPublication).where(MetaAdsAdSetPublication.id == UUID(ad_set_payload["id"]))
    )
    ad_set = result.scalar_one()
    ad_set.remote_status = "ACTIVE"
    await db_session.commit()

    response = await client.post(
        _ads_path(campaign_id, pub["id"]),
        headers=_headers(token),
        json={"creative_publication_id": str(creative.id)},
    )
    assert response.status_code == 403
    assert "paused" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ad_invokes_remote_paused_hierarchy_guard(client: AsyncClient, db_session: AsyncSession, monkeypatch):
    token = await _register(client, "meta-ad-remote-guard@test.com")
    campaign_id, pub, ad_set = await _setup_ad_set(client, token)
    creative = await _create_creative_record(db_session, pub["id"], ad_set["id"], suffix="guard")

    async def refuse(*args, **kwargs):
        raise ForbiddenException("Remote Meta Ad Set must be PAUSED before continuing")

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_ads.MetaAdsRemoteStateGuard.require_paused_hierarchy",
        refuse,
    )
    response = await client.post(
        _ads_path(campaign_id, pub["id"]),
        headers=_headers(token),
        json={"creative_publication_id": str(creative.id)},
    )
    assert response.status_code == 403
    assert "remote" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ad_requires_management_scope(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-ad-scope@test.com")
    campaign_id, pub, ad_set = await _setup_ad_set(client, token)
    creative = await _create_creative_record(db_session, pub["id"], ad_set["id"], suffix="scope")
    result = await db_session.execute(select(MetaAdsConnection).where(MetaAdsConnection.is_active == True))
    connection = result.scalar_one()
    connection.scopes = "ads_read"
    await db_session.commit()

    response = await client.post(
        _ads_path(campaign_id, pub["id"]),
        headers=_headers(token),
        json={"creative_publication_id": str(creative.id)},
    )
    assert response.status_code == 403
    assert "ads_management" in response.json()["detail"]


@pytest.mark.asyncio
async def test_meta_ad_provider_failure_is_sanitized(client: AsyncClient, db_session: AsyncSession, monkeypatch):
    token = await _register(client, "meta-ad-provider@test.com")
    campaign_id, pub, ad_set = await _setup_ad_set(client, token)
    creative = await _create_creative_record(db_session, pub["id"], ad_set["id"], suffix="provider")

    class FailingProvider:
        async def ensure_paused_ad(self, *args, **kwargs):
            raise MetaAdsProviderError("upstream-private-detail")

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_ads.get_meta_ads_ad_provider",
        lambda: FailingProvider(),
    )
    response = await client.post(
        _ads_path(campaign_id, pub["id"]),
        headers=_headers(token),
        json={"creative_publication_id": str(creative.id)},
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "Meta Ads Ad creation failed"
    assert "upstream-private-detail" not in response.text


@pytest.mark.asyncio
async def test_meta_ad_refuses_provider_response_not_paused(client: AsyncClient, db_session: AsyncSession, monkeypatch):
    token = await _register(client, "meta-ad-provider-active@test.com")
    campaign_id, pub, ad_set = await _setup_ad_set(client, token)
    creative = await _create_creative_record(db_session, pub["id"], ad_set["id"], suffix="provider-active")

    class UnsafeProvider:
        async def ensure_paused_ad(self, *args, **kwargs):
            return {"id": "unsafe-remote-ad", "status": "ACTIVE", "reused": False}

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_ads.get_meta_ads_ad_provider",
        lambda: UnsafeProvider(),
    )
    response = await client.post(
        _ads_path(campaign_id, pub["id"]),
        headers=_headers(token),
        json={"creative_publication_id": str(creative.id)},
    )
    assert response.status_code == 502
    assert "paused" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_ad_rejects_malformed_creative_id(client: AsyncClient):
    token = await _register(client, "meta-ad-malformed@test.com")
    campaign_id, pub, _ = await _setup_ad_set(client, token)
    response = await client.post(
        _ads_path(campaign_id, pub["id"]),
        headers=_headers(token),
        json={"creative_publication_id": "not-a-uuid"},
    )
    assert response.status_code == 422
