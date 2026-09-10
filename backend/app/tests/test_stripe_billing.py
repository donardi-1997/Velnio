import hashlib
import hmac
import json
import time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.plan import Plan


async def _seed_plans(db: AsyncSession) -> None:
    db.add_all(
        [
            Plan(code="FREE", name="Free", monthly_price=0, included_credits=10, max_stores=1, max_products_per_month=2),
            Plan(code="LAUNCH", name="Starter", monthly_price=29, included_credits=100, max_stores=1, max_products_per_month=10),
            Plan(code="GROWTH", name="Growth", monthly_price=79, included_credits=400, max_stores=3, max_products_per_month=30),
            Plan(code="SCALE", name="Scale", monthly_price=149, included_credits=1200, max_stores=10, max_products_per_month=100),
        ]
    )
    await db.commit()


async def _register(client: AsyncClient, email: str = "billing@test.com") -> tuple[str, dict]:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Test12345!",
            "first_name": "Billing",
            "last_name": "Owner",
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


def _stripe_signature(payload: bytes, secret: str) -> str:
    timestamp = int(time.time())
    signed = f"{timestamp}.{payload.decode()}".encode()
    signature = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


@pytest.mark.asyncio
async def test_mock_checkout_activates_trial_and_entitlements(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await _seed_plans(db_session)
    _, headers = await _register(client)

    free = await client.get("/api/billing/entitlements", headers=headers)
    assert free.status_code == 200
    assert free.json()["plan_code"] == "FREE"
    assert free.json()["max_stores"] == 1

    checkout = await client.post(
        "/api/billing/checkout",
        headers=headers,
        json={"plan_code": "GROWTH"},
    )
    assert checkout.status_code == 200
    assert "checkout=success" in checkout.json()["url"]

    subscription = await client.get("/api/billing/subscription", headers=headers)
    assert subscription.status_code == 200
    assert subscription.json()["status"] == "TRIALING"
    assert subscription.json()["plan"]["code"] == "GROWTH"

    entitlements = await client.get("/api/billing/entitlements", headers=headers)
    assert entitlements.status_code == 200
    assert entitlements.json()["max_stores"] == 3
    assert entitlements.json()["max_products_per_month"] == 30

    portal = await client.post("/api/billing/portal", headers=headers)
    assert portal.status_code == 200
    assert "portal=mock" in portal.json()["url"]


@pytest.mark.asyncio
async def test_free_plan_enforces_product_and_store_limits(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await _seed_plans(db_session)
    _, headers = await _register(client, "limits@test.com")

    first_store = await client.post(
        "/api/stores/mock-connect",
        headers=headers,
        json={"name": "Store 1", "shop_domain": "store-1.myshopify.com", "country": "US", "currency": "USD"},
    )
    assert first_store.status_code == 201
    second_store = await client.post(
        "/api/stores/mock-connect",
        headers=headers,
        json={"name": "Store 2", "shop_domain": "store-2.myshopify.com", "country": "US", "currency": "USD"},
    )
    assert second_store.status_code == 402
    assert "Store limit reached" in second_store.json()["detail"]

    for index in range(2):
        response = await client.post(
            "/api/products",
            headers=headers,
            json={"name": f"Product {index + 1}"},
        )
        assert response.status_code == 201

    blocked = await client.post(
        "/api/products",
        headers=headers,
        json={"name": "Product 3"},
    )
    assert blocked.status_code == 402
    assert "Monthly product limit reached" in blocked.json()["detail"]


@pytest.mark.asyncio
async def test_stripe_webhook_syncs_subscription_and_is_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    await _seed_plans(db_session)
    _, headers = await _register(client, "stripe-webhook@test.com")

    workspace = await client.get("/api/workspace", headers=headers)
    assert workspace.status_code == 200
    workspace_id = workspace.json()["id"]

    monkeypatch.setattr(settings, "BILLING_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_velnio")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_velnio")
    monkeypatch.setattr(settings, "STRIPE_PRICE_GROWTH", "price_growth_test")

    now = int(time.time())
    event = {
        "id": "evt_velnio_subscription_1",
        "object": "event",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_velnio_1",
                "object": "subscription",
                "status": "trialing",
                "customer": "cus_velnio_1",
                "metadata": {
                    "workspace_id": workspace_id,
                    "plan_code": "GROWTH",
                },
                "cancel_at_period_end": False,
                "trial_end": now + 7 * 24 * 60 * 60,
                "items": {
                    "data": [
                        {
                            "price": {"id": "price_growth_test"},
                            "current_period_start": now,
                            "current_period_end": now + 30 * 24 * 60 * 60,
                        }
                    ]
                },
            }
        },
    }
    payload = json.dumps(event, separators=(",", ":")).encode()
    signature = _stripe_signature(payload, settings.STRIPE_WEBHOOK_SECRET)

    first = await client.post(
        "/api/billing/webhook",
        content=payload,
        headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
    )
    assert first.status_code == 200
    assert first.json() == {"received": True, "duplicate": False}

    subscription = await client.get("/api/billing/subscription", headers=headers)
    assert subscription.status_code == 200
    assert subscription.json()["provider"] == "STRIPE"
    assert subscription.json()["status"] == "TRIALING"
    assert subscription.json()["plan"]["code"] == "GROWTH"

    credits_after_first = await client.get("/api/credits", headers=headers)
    assert credits_after_first.status_code == 200
    assert credits_after_first.json()["balance"] == 410

    duplicate = await client.post(
        "/api/billing/webhook",
        content=payload,
        headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
    )
    assert duplicate.status_code == 200
    assert duplicate.json() == {"received": True, "duplicate": True}

    credits_after_duplicate = await client.get("/api/credits", headers=headers)
    assert credits_after_duplicate.json()["balance"] == 410


@pytest.mark.asyncio
async def test_stripe_webhook_rejects_invalid_signature(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "BILLING_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_velnio")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_velnio")

    response = await client.post(
        "/api/billing/webhook",
        content=b'{"id":"evt_bad","type":"customer.subscription.updated"}',
        headers={"Stripe-Signature": "t=1,v1=invalid", "Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid billing webhook signature"
