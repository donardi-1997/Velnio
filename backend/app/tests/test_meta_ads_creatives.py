from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignStatus
from app.models.meta_ads import (
    MetaAdsAdSetPublication,
    MetaAdsCampaignPublication,
    MetaAdsConnection,
    MetaAdsCreativePublication,
)
from app.models.product import Product, ProductImage, ProductStatus, SourceType
from app.models.store import Store, StoreStatus
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError


async def _register(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "Test12345!", "first_name": "Meta", "last_name": "Creative"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _creative_path(campaign_id: str, publication_id: str) -> str:
    return f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication_id}/creatives"


async def _setup_meta(client: AsyncClient, token: str) -> tuple[str, dict]:
    headers = _headers(token)
    campaign = await client.post(
        "/api/campaigns",
        headers=headers,
        json={"name": "Meta Creative launch", "target_country": "CO", "currency": "COP"},
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
    return campaign_id, pub


async def _prepare_shopify_asset(
    db_session: AsyncSession,
    campaign_id: str,
    *,
    published: bool = True,
    selected: bool = True,
) -> ProductImage:
    result = await db_session.execute(select(Campaign).where(Campaign.id == UUID(campaign_id)))
    campaign = result.scalar_one()

    store = Store(
        workspace_id=campaign.workspace_id,
        name="Creative Store",
        shop_domain="velnio-creative.myshopify.com",
        status=StoreStatus.CONNECTED,
        country="CO",
        currency="COP",
    )
    db_session.add(store)
    await db_session.flush()

    product = Product(
        workspace_id=campaign.workspace_id,
        store_id=store.id,
        name="Creative Product",
        source_type=SourceType.MANUAL,
        currency="COP",
        target_country="CO",
        target_language="es",
        status=ProductStatus.READY,
    )
    db_session.add(product)
    await db_session.flush()

    image = ProductImage(
        product_id=product.id,
        campaign_id=campaign.id,
        image_url="https://cdn.example.test/velnio/meta-social.jpg",
        image_type="campaign",
        position=0,
        generated_by_ai="true",
        source_type="AI_GENERATED",
        purpose="SOCIAL",
        selected=selected,
    )
    db_session.add(image)

    campaign.store_id = store.id
    campaign.product_id = product.id
    if published:
        campaign.status = CampaignStatus.PUBLISHED
        campaign.external_page_id = "gid://shopify/Page/123"
        campaign.external_page_handle = "velnio-campaign-creative"
        campaign.external_page_url = "https://velnio-creative.myshopify.com/pages/velnio-campaign-creative"

    await db_session.commit()
    await db_session.refresh(image)
    return image


async def _ready_context(
    client: AsyncClient,
    db_session: AsyncSession,
    token: str,
    *,
    published: bool = True,
    selected: bool = True,
) -> tuple[str, dict, ProductImage]:
    campaign_id, pub = await _setup_meta(client, token)
    image = await _prepare_shopify_asset(
        db_session,
        campaign_id,
        published=published,
        selected=selected,
    )
    return campaign_id, pub, image


def _payload(image_id: UUID, *, text: str = "Discover the Velnio offer today.") -> dict:
    return {
        "product_image_id": str(image_id),
        "primary_text": text,
        "headline": "Launch offer",
        "call_to_action": "SHOP_NOW",
    }


@pytest.mark.asyncio
async def test_meta_creative_list_is_empty_before_creation(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-creative-empty@test.com")
    campaign_id, pub, _ = await _ready_context(client, db_session, token)
    response = await client.get(_creative_path(campaign_id, pub["id"]), headers=_headers(token))
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_meta_creative_uses_persisted_shopify_url_and_selected_asset(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-creative-create@test.com")
    campaign_id, pub, image = await _ready_context(client, db_session, token)
    response = await client.post(
        _creative_path(campaign_id, pub["id"]),
        headers=_headers(token),
        json=_payload(image.id),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["destination_url"] == "https://velnio-creative.myshopify.com/pages/velnio-campaign-creative"
    assert payload["image_url"] == image.image_url
    assert payload["product_image_id"] == str(image.id)
    assert payload["page_id"] == "1000000001601"
    assert payload["instagram_account_id"] == "1000000001701"
    assert payload["call_to_action"] == "SHOP_NOW"
    assert payload["reused"] is False
    assert payload["remote_creative_id"].startswith("mock_meta_creative_")


@pytest.mark.asyncio
async def test_meta_creative_retry_is_idempotent(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-creative-idempotent@test.com")
    campaign_id, pub, image = await _ready_context(client, db_session, token)
    path = _creative_path(campaign_id, pub["id"])
    first = await client.post(path, headers=_headers(token), json=_payload(image.id))
    second = await client.post(path, headers=_headers(token), json=_payload(image.id))
    assert first.status_code == second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["remote_creative_id"] == first.json()["remote_creative_id"]
    assert second.json()["reused"] is True
    result = await db_session.execute(
        select(MetaAdsCreativePublication).where(
            MetaAdsCreativePublication.campaign_publication_id == UUID(pub["id"])
        )
    )
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_meta_creative_allows_distinct_content_variants(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-creative-variants@test.com")
    campaign_id, pub, image = await _ready_context(client, db_session, token)
    path = _creative_path(campaign_id, pub["id"])
    first = await client.post(path, headers=_headers(token), json=_payload(image.id, text="Variant A"))
    second = await client.post(path, headers=_headers(token), json=_payload(image.id, text="Variant B"))
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] != second.json()["id"]
    listed = await client.get(path, headers=_headers(token))
    assert listed.status_code == 200
    assert len(listed.json()) == 2


@pytest.mark.asyncio
async def test_meta_creative_requires_shopify_publication(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-creative-shopify@test.com")
    campaign_id, pub, image = await _ready_context(client, db_session, token, published=False)
    response = await client.post(
        _creative_path(campaign_id, pub["id"]), headers=_headers(token), json=_payload(image.id)
    )
    assert response.status_code == 400
    assert "shopify" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_creative_requires_selected_campaign_asset(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-creative-selected@test.com")
    campaign_id, pub, image = await _ready_context(client, db_session, token, selected=False)
    response = await client.post(
        _creative_path(campaign_id, pub["id"]), headers=_headers(token), json=_payload(image.id)
    )
    assert response.status_code == 400
    assert "select" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_creative_rejects_shopify_url_from_other_host(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-creative-host@test.com")
    campaign_id, pub, image = await _ready_context(client, db_session, token)
    result = await db_session.execute(select(Campaign).where(Campaign.id == UUID(campaign_id)))
    campaign = result.scalar_one()
    campaign.external_page_url = "https://other-shop.myshopify.com/pages/velnio-campaign-creative"
    await db_session.commit()
    response = await client.post(
        _creative_path(campaign_id, pub["id"]), headers=_headers(token), json=_payload(image.id)
    )
    assert response.status_code == 400
    assert "does not belong" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_creative_refuses_non_paused_ad_set(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-creative-active@test.com")
    campaign_id, pub, image = await _ready_context(client, db_session, token)
    result = await db_session.execute(
        select(MetaAdsAdSetPublication).where(
            MetaAdsAdSetPublication.campaign_publication_id == UUID(pub["id"])
        )
    )
    ad_set = result.scalar_one()
    ad_set.remote_status = "ACTIVE"
    await db_session.commit()
    response = await client.post(
        _creative_path(campaign_id, pub["id"]), headers=_headers(token), json=_payload(image.id)
    )
    assert response.status_code == 403
    assert "paused" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_creative_revalidates_page(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-creative-page@test.com")
    campaign_id, pub, image = await _ready_context(client, db_session, token)
    result = await db_session.execute(
        select(MetaAdsCampaignPublication).where(MetaAdsCampaignPublication.id == UUID(pub["id"]))
    )
    publication = result.scalar_one()
    publication.page_id = "999999"
    await db_session.commit()
    response = await client.post(
        _creative_path(campaign_id, pub["id"]), headers=_headers(token), json=_payload(image.id)
    )
    assert response.status_code == 403
    assert "page" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_creative_requires_management_scope(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-creative-scope@test.com")
    campaign_id, pub, image = await _ready_context(client, db_session, token)
    result = await db_session.execute(select(MetaAdsConnection).where(MetaAdsConnection.is_active == True))
    connection = result.scalar_one()
    connection.scopes = "ads_read"
    await db_session.commit()
    response = await client.post(
        _creative_path(campaign_id, pub["id"]), headers=_headers(token), json=_payload(image.id)
    )
    assert response.status_code == 403
    assert "ads_management" in response.json()["detail"]


@pytest.mark.asyncio
async def test_meta_creative_is_workspace_isolated(client: AsyncClient, db_session: AsyncSession):
    owner = await _register(client, "meta-creative-owner@test.com")
    other = await _register(client, "meta-creative-other@test.com")
    campaign_id, pub, image = await _ready_context(client, db_session, owner)
    response = await client.post(
        _creative_path(campaign_id, pub["id"]), headers=_headers(other), json=_payload(image.id)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_meta_creative_provider_failure_is_sanitized(client: AsyncClient, db_session: AsyncSession, monkeypatch):
    token = await _register(client, "meta-creative-provider@test.com")
    campaign_id, pub, image = await _ready_context(client, db_session, token)

    class FailingProvider:
        async def ensure_standalone_creative(self, *args, **kwargs):
            raise MetaAdsProviderError("upstream-private-detail")

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_creatives.get_meta_ads_creative_provider",
        lambda: FailingProvider(),
    )
    response = await client.post(
        _creative_path(campaign_id, pub["id"]), headers=_headers(token), json=_payload(image.id)
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "Meta Ads Creative creation failed"
    assert "upstream-private-detail" not in response.text


@pytest.mark.asyncio
async def test_meta_creative_rejects_whitespace_primary_text(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-creative-text@test.com")
    campaign_id, pub, image = await _ready_context(client, db_session, token)
    response = await client.post(
        _creative_path(campaign_id, pub["id"]),
        headers=_headers(token),
        json=_payload(image.id, text="   "),
    )
    assert response.status_code == 400
    assert "primary text" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_creative_rejects_unsupported_cta(client: AsyncClient, db_session: AsyncSession):
    token = await _register(client, "meta-creative-cta@test.com")
    campaign_id, pub, image = await _ready_context(client, db_session, token)
    payload = _payload(image.id)
    payload["call_to_action"] = "BUY_NOW"
    response = await client.post(
        _creative_path(campaign_id, pub["id"]), headers=_headers(token), json=payload
    )
    assert response.status_code == 422
