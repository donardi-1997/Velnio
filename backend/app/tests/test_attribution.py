import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.campaign import Campaign
from app.models.tracking import LandingVariant, TrackingEvent
from app.services.experiments import ExperimentAnalysisService


async def _register_and_product(client: AsyncClient, email: str = "attribution@test.com"):
    registered = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Test12345!",
            "first_name": "Attr",
            "last_name": "User",
        },
    )
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    product = await client.post(
        "/api/products",
        json={"name": "Attributed Product", "selling_price": 49.99},
        headers=headers,
    )
    return headers, product.json()["id"]


async def _create_campaign(client: AsyncClient, headers: dict, product_id: str, **extra):
    payload = {"name": "Attributed Campaign", "selling_price": 49.99, **extra}
    response = await client.post(
        f"/api/campaigns/by-product/{product_id}",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_new_campaign_gets_secure_tracking_key(
    client: AsyncClient,
    db_session: AsyncSession,
):
    headers, product_id = await _register_and_product(client)
    created = await _create_campaign(client, headers, product_id)
    campaign = (
        await db_session.execute(select(Campaign).where(Campaign.id == UUID(created["id"])))
    ).scalar_one()
    assert campaign.tracking_key
    assert 32 <= len(campaign.tracking_key) <= 64


@pytest.mark.asyncio
async def test_landing_generation_creates_control_variant(
    client: AsyncClient,
    db_session: AsyncSession,
):
    headers, product_id = await _register_and_product(client)
    campaign = await _create_campaign(client, headers, product_id)
    campaign_id = campaign["id"]

    angles = (
        await client.post(
            f"/api/campaigns/{campaign_id}/angles/generate",
            headers=headers,
        )
    ).json()
    await client.post(
        f"/api/campaigns/{campaign_id}/angles/{angles[0]['id']}/select",
        headers=headers,
    )
    await client.post(f"/api/campaigns/{campaign_id}/offer/generate", headers=headers)
    landing = await client.post(
        f"/api/campaigns/{campaign_id}/landing/generate",
        headers=headers,
    )
    assert landing.status_code == 200

    control = (
        await db_session.execute(
            select(LandingVariant).where(
                LandingVariant.campaign_id == UUID(campaign_id),
                LandingVariant.variant_key == "A",
            )
        )
    ).scalar_one()
    assert control.name == "Control"
    assert control.status == "ACTIVE"
    assert control.traffic_weight == 100
    assert str(control.landing_page_id) == landing.json()["id"]


@pytest.mark.asyncio
async def test_beacon_attributes_valid_variant_and_rejects_cross_campaign_variant(
    client: AsyncClient,
    db_session: AsyncSession,
):
    headers, product_id = await _register_and_product(client)
    first = await _create_campaign(client, headers, product_id, name="First Campaign")
    second = await _create_campaign(client, headers, product_id, name="Second Campaign")
    first_model = (
        await db_session.execute(select(Campaign).where(Campaign.id == UUID(first["id"])))
    ).scalar_one()
    second_variant = LandingVariant(
        campaign_id=UUID(second["id"]),
        name="Other",
        variant_key="A",
        status="ACTIVE",
        traffic_weight=100,
    )
    first_variant = LandingVariant(
        campaign_id=first_model.id,
        name="Control",
        variant_key="A",
        status="ACTIVE",
        traffic_weight=100,
    )
    db_session.add_all([first_variant, second_variant])
    await db_session.commit()

    session_id = str(uuid4())
    valid = await client.post(
        f"/api/tracking/beacon/{first_model.tracking_key}",
        data={
            "event_type": "PAGE_VIEW",
            "session_id": session_id,
            "landing_variant_id": str(first_variant.id),
        },
    )
    assert valid.status_code == 204

    cross_campaign = await client.post(
        f"/api/tracking/beacon/{first_model.tracking_key}",
        data={
            "event_type": "CTA_CLICK",
            "session_id": str(uuid4()),
            "landing_variant_id": str(second_variant.id),
        },
    )
    assert cross_campaign.status_code == 400

    event = (
        await db_session.execute(
            select(TrackingEvent).where(TrackingEvent.session_id == session_id)
        )
    ).scalar_one()
    assert event.landing_variant_id == first_variant.id


@pytest.mark.asyncio
async def test_beacon_rejects_purchase(client: AsyncClient, db_session: AsyncSession):
    headers, product_id = await _register_and_product(client)
    created = await _create_campaign(client, headers, product_id)
    campaign = (
        await db_session.execute(select(Campaign).where(Campaign.id == UUID(created["id"])))
    ).scalar_one()
    response = await client.post(
        f"/api/tracking/beacon/{campaign.tracking_key}",
        data={"event_type": "PURCHASE", "session_id": str(uuid4())},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_statistical_winner_uses_real_variant_metrics(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(ExperimentAnalysisService, "MIN_SESSIONS_PER_VARIANT", 10)
    monkeypatch.setattr(ExperimentAnalysisService, "MIN_PURCHASES", 2)

    headers, product_id = await _register_and_product(client)
    created = await _create_campaign(client, headers, product_id)
    campaign = (
        await db_session.execute(select(Campaign).where(Campaign.id == UUID(created["id"])))
    ).scalar_one()
    control = LandingVariant(
        campaign_id=campaign.id,
        name="Control",
        variant_key="A",
        status="ACTIVE",
        traffic_weight=50,
    )
    challenger = LandingVariant(
        campaign_id=campaign.id,
        name="Challenger",
        variant_key="B",
        status="ACTIVE",
        traffic_weight=50,
    )
    db_session.add_all([control, challenger])
    await db_session.flush()

    now = datetime.now(timezone.utc)
    events = []
    for variant in (control, challenger):
        for index in range(10):
            events.append(
                TrackingEvent(
                    workspace_id=campaign.workspace_id,
                    campaign_id=campaign.id,
                    landing_variant_id=variant.id,
                    event_type="PAGE_VIEW",
                    session_id=f"{variant.variant_key}-session-{index}",
                    visitor_id=f"{variant.variant_key}-visitor-{index}",
                    occurred_at=now,
                )
            )
    for index in range(2):
        events.append(
            TrackingEvent(
                workspace_id=campaign.workspace_id,
                campaign_id=campaign.id,
                landing_variant_id=control.id,
                event_type="PURCHASE",
                session_id=f"A-session-{index}",
                revenue=49.99,
                external_event_id=f"control-{index}",
                occurred_at=now,
            )
        )
    for index in range(8):
        events.append(
            TrackingEvent(
                workspace_id=campaign.workspace_id,
                campaign_id=campaign.id,
                landing_variant_id=challenger.id,
                event_type="PURCHASE",
                session_id=f"B-session-{index}",
                revenue=49.99,
                external_event_id=f"challenger-{index}",
                occurred_at=now,
            )
        )
    db_session.add_all(events)
    await db_session.commit()

    response = await client.get(
        f"/api/campaigns/{campaign.id}/performance/winner",
        headers=headers,
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "leader"
    assert result["variant_id"] == str(challenger.id)
    assert result["confidence"] > 0.95
    assert result["lift"] > 0


def _signed_webhook(raw: bytes, secret: str) -> str:
    return base64.b64encode(
        hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest()
    ).decode("ascii")


@pytest.mark.asyncio
async def test_shopify_order_webhook_attributes_purchase_and_is_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "SHOPIFY_API_SECRET", "webhook-secret")
    headers, product_id = await _register_and_product(client)
    store_response = await client.post(
        "/api/stores/mock-connect",
        json={
            "name": "Attribution Shop",
            "shop_domain": "attribution-shop.myshopify.com",
            "country": "US",
            "currency": "USD",
        },
        headers=headers,
    )
    assert store_response.status_code == 201
    store_id = store_response.json()["id"]
    created = await _create_campaign(client, headers, product_id, store_id=store_id)
    campaign = (
        await db_session.execute(select(Campaign).where(Campaign.id == UUID(created["id"])))
    ).scalar_one()
    campaign.external_product_id = "gid://shopify/Product/98765"
    variant = LandingVariant(
        campaign_id=campaign.id,
        name="Control",
        variant_key="A",
        status="ACTIVE",
        traffic_weight=100,
    )
    db_session.add(variant)
    await db_session.commit()

    payload = {
        "id": 777,
        "currency": "USD",
        "line_items": [
            {
                "id": 888,
                "product_id": 98765,
                "price": "49.99",
                "quantity": 2,
                "discount_allocations": [{"amount": "10.00"}],
                "properties": [
                    {"name": "_velnio_tracking_key", "value": campaign.tracking_key},
                    {"name": "_velnio_variant_id", "value": str(variant.id)},
                    {"name": "_velnio_session_id", "value": "session-shopify-1"},
                    {"name": "_velnio_visitor_id", "value": "visitor-shopify-1"},
                ],
            }
        ],
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    webhook_headers = {
        "Content-Type": "application/json",
        "X-Shopify-Hmac-Sha256": _signed_webhook(raw, "webhook-secret"),
        "X-Shopify-Shop-Domain": "attribution-shop.myshopify.com",
        "X-Shopify-Topic": "orders/create",
    }

    first = await client.post(
        "/api/stores/shopify/webhooks/orders-create",
        content=raw,
        headers=webhook_headers,
    )
    assert first.status_code == 200
    assert first.json()["events_accepted"] == 1

    duplicate = await client.post(
        "/api/stores/shopify/webhooks/orders-create",
        content=raw,
        headers=webhook_headers,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["events_accepted"] == 0

    purchases = (
        await db_session.execute(
            select(TrackingEvent).where(
                TrackingEvent.campaign_id == campaign.id,
                TrackingEvent.event_type == "PURCHASE",
            )
        )
    ).scalars().all()
    assert len(purchases) == 1
    purchase = purchases[0]
    assert purchase.landing_variant_id == variant.id
    assert purchase.session_id == "session-shopify-1"
    assert purchase.revenue == pytest.approx(89.98)
    assert purchase.external_event_id == "shopify-order:777:line:888"


@pytest.mark.asyncio
async def test_shopify_order_webhook_ignores_wrong_product_identity(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "SHOPIFY_API_SECRET", "webhook-secret")
    headers, product_id = await _register_and_product(client)
    store_response = await client.post(
        "/api/stores/mock-connect",
        json={"name": "Shop", "shop_domain": "safe-shop.myshopify.com"},
        headers=headers,
    )
    created = await _create_campaign(
        client,
        headers,
        product_id,
        store_id=store_response.json()["id"],
    )
    campaign = (
        await db_session.execute(select(Campaign).where(Campaign.id == UUID(created["id"])))
    ).scalar_one()
    campaign.external_product_id = "gid://shopify/Product/111"
    await db_session.commit()

    payload = {
        "id": 778,
        "currency": "USD",
        "line_items": [
            {
                "id": 889,
                "product_id": 999,
                "price": "49.99",
                "quantity": 1,
                "properties": [
                    {"name": "_velnio_tracking_key", "value": campaign.tracking_key},
                    {"name": "_velnio_session_id", "value": "tampered"},
                ],
            }
        ],
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    response = await client.post(
        "/api/stores/shopify/webhooks/orders-create",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Hmac-Sha256": _signed_webhook(raw, "webhook-secret"),
            "X-Shopify-Shop-Domain": "safe-shop.myshopify.com",
            "X-Shopify-Topic": "orders/create",
        },
    )
    assert response.status_code == 200
    assert response.json()["events_accepted"] == 0


@pytest.mark.asyncio
async def test_shopify_order_webhook_rejects_invalid_hmac(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "SHOPIFY_API_SECRET", "webhook-secret")
    response = await client.post(
        "/api/stores/shopify/webhooks/orders-create",
        content=b'{"id":1,"line_items":[]}',
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Hmac-Sha256": "invalid",
            "X-Shopify-Shop-Domain": "valid-shop.myshopify.com",
            "X-Shopify-Topic": "orders/create",
        },
    )
    assert response.status_code == 401
