from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
import stripe

from app.core.config import settings
from app.core.exceptions import BadGatewayException, BadRequestException


@dataclass(frozen=True)
class BillingSession:
    url: str
    session_id: str | None = None


class StripeBillingProvider:
    API_BASE = "https://api.stripe.com/v1"

    def __init__(self) -> None:
        if not settings.STRIPE_SECRET_KEY:
            raise BadGatewayException("Billing provider is not configured")
        self.secret_key = settings.STRIPE_SECRET_KEY
        self.timeout = settings.STRIPE_REQUEST_TIMEOUT_SECONDS

    def price_id_for_plan(self, plan_code: str) -> str:
        mapping = {
            "LAUNCH": settings.STRIPE_PRICE_STARTER,
            "GROWTH": settings.STRIPE_PRICE_GROWTH,
            "SCALE": settings.STRIPE_PRICE_SCALE,
        }
        price_id = mapping.get(plan_code.upper(), "")
        if not price_id:
            raise BadGatewayException("Billing price is not configured")
        return price_id

    def plan_code_for_price(self, price_id: str | None) -> str | None:
        if not price_id:
            return None
        mapping = {
            settings.STRIPE_PRICE_STARTER: "LAUNCH",
            settings.STRIPE_PRICE_GROWTH: "GROWTH",
            settings.STRIPE_PRICE_SCALE: "SCALE",
        }
        return mapping.get(price_id)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    f"{self.API_BASE}{path}",
                    headers=headers,
                    data=data,
                )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RequestError) as exc:
            raise BadGatewayException("Billing provider is unavailable") from exc

        if response.status_code >= 400:
            raise BadGatewayException("Billing provider rejected the request")

        try:
            payload = response.json()
        except ValueError as exc:
            raise BadGatewayException("Billing provider returned an invalid response") from exc
        if not isinstance(payload, dict):
            raise BadGatewayException("Billing provider returned an invalid response")
        return payload

    async def create_checkout_session(
        self,
        *,
        workspace_id: str,
        user_id: str,
        email: str,
        plan_code: str,
        customer_id: str | None,
        allow_trial: bool,
    ) -> BillingSession:
        price_id = self.price_id_for_plan(plan_code)
        data: dict[str, Any] = {
            "mode": "subscription",
            "success_url": f"{settings.FRONTEND_URL.rstrip('/')}/billing?checkout=success",
            "cancel_url": f"{settings.FRONTEND_URL.rstrip('/')}/billing?checkout=cancelled",
            "client_reference_id": workspace_id,
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "metadata[workspace_id]": workspace_id,
            "metadata[plan_code]": plan_code,
            "metadata[user_id]": user_id,
            "subscription_data[metadata][workspace_id]": workspace_id,
            "subscription_data[metadata][plan_code]": plan_code,
            "subscription_data[metadata][user_id]": user_id,
        }
        if customer_id:
            data["customer"] = customer_id
        else:
            data["customer_email"] = email
        if allow_trial and settings.STRIPE_TRIAL_DAYS > 0:
            data["subscription_data[trial_period_days]"] = str(settings.STRIPE_TRIAL_DAYS)

        payload = await self._request("POST", "/checkout/sessions", data=data)
        url = payload.get("url")
        session_id = payload.get("id")
        if not isinstance(url, str) or not url:
            raise BadGatewayException("Billing provider returned an invalid checkout session")
        return BillingSession(url=url, session_id=session_id if isinstance(session_id, str) else None)

    async def create_portal_session(self, *, customer_id: str) -> BillingSession:
        payload = await self._request(
            "POST",
            "/billing_portal/sessions",
            data={
                "customer": customer_id,
                "return_url": f"{settings.FRONTEND_URL.rstrip('/')}/billing",
            },
        )
        url = payload.get("url")
        session_id = payload.get("id")
        if not isinstance(url, str) or not url:
            raise BadGatewayException("Billing provider returned an invalid portal session")
        return BillingSession(url=url, session_id=session_id if isinstance(session_id, str) else None)

    async def retrieve_subscription(self, subscription_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/subscriptions/{subscription_id}")

    def verify_webhook(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise BadGatewayException("Billing webhook is not configured")
        if not signature:
            raise BadRequestException("Missing billing webhook signature")
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=settings.STRIPE_WEBHOOK_SECRET,
                tolerance=300,
            )
        except Exception as exc:
            raise BadRequestException("Invalid billing webhook signature") from exc

        event_dict = event.to_dict()
        if not isinstance(event_dict, dict):
            raise BadRequestException("Invalid billing webhook payload")
        if not isinstance(event_dict.get("id"), str) or not isinstance(event_dict.get("type"), str):
            raise BadRequestException("Invalid billing webhook payload")
        return event_dict


class MockBillingProvider:
    def price_id_for_plan(self, plan_code: str) -> str:
        return f"mock_price_{plan_code.lower()}"

    def plan_code_for_price(self, price_id: str | None) -> str | None:
        if not price_id or not price_id.startswith("mock_price_"):
            return None
        return price_id.removeprefix("mock_price_").upper()

    async def create_checkout_session(self, **kwargs: Any) -> BillingSession:
        plan_code = str(kwargs["plan_code"])
        query = urlencode({"checkout": "success", "mock": "1", "plan": plan_code})
        return BillingSession(
            url=f"{settings.FRONTEND_URL.rstrip('/')}/billing?{query}",
            session_id=f"mock_checkout_{plan_code.lower()}",
        )

    async def create_portal_session(self, *, customer_id: str) -> BillingSession:
        return BillingSession(
            url=f"{settings.FRONTEND_URL.rstrip('/')}/billing?portal=mock",
            session_id="mock_portal",
        )

    async def retrieve_subscription(self, subscription_id: str) -> dict[str, Any]:
        raise BadRequestException("Mock billing does not retrieve remote subscriptions")

    def verify_webhook(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        raise BadRequestException("Webhooks are only available with Stripe billing")


def get_billing_provider() -> StripeBillingProvider | MockBillingProvider:
    provider = settings.BILLING_PROVIDER.strip().lower()
    if provider == "mock":
        return MockBillingProvider()
    if provider == "stripe":
        return StripeBillingProvider()
    raise BadGatewayException("Unsupported billing provider")
