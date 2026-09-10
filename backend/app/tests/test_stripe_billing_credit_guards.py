import hashlib
import hmac
import json
import time

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.plan import Plan
from app.models.workspace import WorkspaceMember
from app.modules.billing.infrastructure.provider import StripeBillingProvider


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


async def _register(client: AsyncClient, email: str) -> tuple[dict, str]:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Test12345!",
            "first_name": "Billing",
            "last_name": "Guard",
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, token


def _signature(payload: bytes, secret: str) -> str:
    timestamp = int(time.time())
    signed = f"{timestamp}.{payload.decode()}".encode()
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def _remote_subscription(*, workspace_id: str, plan_code: str, price_id: str, status: str = "trialing") -> dict:
    now = int(time.time())
    return {
        "id": "sub_credit_guard",
        "status": status,
        "customer": "cus_credit_guard",
        "metadata": {"workspace_id": workspace_id, "plan_code": plan_code},
        "cancel_at_period_end": False,
        "trial_end": now + 7 * 24 * 60 * 60 if status == "trialing" else None,
        "items": {
            "data": [
                {
                    "price": {"id": price_id},
                    "current_period_start": now,
                    "current_period_end": now + 30 * 24 * 60 * 60,
                }
            ]
        },
    }


@pytest.mark.asyncio
async def test_trial_plan_change_does_not_allocate_trial_credits_twice(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    await _seed_plans(db_session)
    headers, _ = await _register(client, "trial-switch@test.com")
    membership = (await db_session.execute(select(WorkspaceMember))).scalar_one()
    workspace_id = str(membership.workspace_id)

    monkeypatch.setattr(settings, "BILLING_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_velnio")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_velnio")
    monkeypatch.setattr(settings, "STRIPE_PRICE_GROWTH", "price_growth_test")
    monkeypatch.setattr(settings, "STRIPE_PRICE_SCALE", "price_scale_test")

    for event_id, plan_code, price_id in (
        ("evt_trial_growth", "GROWTH", "price_growth_test"),
        ("evt_trial_scale", "SCALE", "price_scale_test"),
    ):
        event = {
            "id": event_id,
            "object": "event",
            "type": "customer.subscription.updated",
            "data": {"object": _remote_subscription(workspace_id=workspace_id, plan_code=plan_code, price_id=price_id)},
        }
        payload = json.dumps(event, separators=(",", ":")).encode()
        response = await client.post(
            "/api/billing/webhook",
            content=payload,
            headers={"Stripe-Signature": _signature(payload, settings.STRIPE_WEBHOOK_SECRET)},
        )
        assert response.status_code == 200

    credits = await client.get("/api/credits", headers=headers)
    assert credits.status_code == 200
    assert credits.json()["balance"] == 410

    subscription = await client.get("/api/billing/subscription", headers=headers)
    assert subscription.json()["plan"]["code"] == "SCALE"


@pytest.mark.asyncio
async def test_proration_invoice_does_not_allocate_monthly_credits(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    await _seed_plans(db_session)
    headers, _ = await _register(client, "proration@test.com")
    membership = (await db_session.execute(select(WorkspaceMember))).scalar_one()
    workspace_id = str(membership.workspace_id)

    monkeypatch.setattr(settings, "BILLING_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_velnio")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_velnio")
    monkeypatch.setattr(settings, "STRIPE_PRICE_GROWTH", "price_growth_test")

    remote = _remote_subscription(
        workspace_id=workspace_id,
        plan_code="GROWTH",
        price_id="price_growth_test",
        status="active",
    )

    async def fake_retrieve(self, subscription_id: str):
        assert subscription_id == "sub_credit_guard"
        return remote

    monkeypatch.setattr(StripeBillingProvider, "retrieve_subscription", fake_retrieve)

    event = {
        "id": "evt_proration_paid",
        "object": "event",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_proration",
                "subscription": "sub_credit_guard",
                "billing_reason": "subscription_update",
            }
        },
    }
    payload = json.dumps(event, separators=(",", ":")).encode()
    response = await client.post(
        "/api/billing/webhook",
        content=payload,
        headers={"Stripe-Signature": _signature(payload, settings.STRIPE_WEBHOOK_SECRET)},
    )
    assert response.status_code == 200

    credits = await client.get("/api/credits", headers=headers)
    assert credits.status_code == 200
    assert credits.json()["balance"] == 10

    subscription = await client.get("/api/billing/subscription", headers=headers)
    assert subscription.json()["status"] == "ACTIVE"
    assert subscription.json()["plan"]["code"] == "GROWTH"
