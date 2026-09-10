from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Sequence
from uuid import UUID

from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.modules.billing.infrastructure.provider import (
    BillingSession,
    MockBillingProvider,
    StripeBillingProvider,
    get_billing_provider,
)
from app.modules.billing.infrastructure.repository import BillingRepository


class SubscriptionService:
    def __init__(
        self,
        repository: BillingRepository,
        provider: StripeBillingProvider | MockBillingProvider | None = None,
    ) -> None:
        self.repository = repository
        self.provider = provider or get_billing_provider()

    async def list_plans(self) -> Sequence[Plan]:
        return await self.repository.list_active_plans()

    async def get_subscription(self, workspace_id: UUID) -> Subscription:
        subscription = await self.repository.get_subscription(workspace_id)
        if subscription is None:
            raise NotFoundException("Subscription")
        return subscription

    async def create_checkout_session(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        email: str,
        plan_code: str,
    ) -> BillingSession:
        normalized_code = plan_code.strip().upper()
        plan = await self.repository.get_plan_by_code(normalized_code)
        if plan is None or plan.monthly_price <= 0:
            raise BadRequestException("Select an active paid plan")

        subscription = await self.repository.get_subscription(workspace_id)
        if subscription and subscription.status in {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
        } and subscription.plan and subscription.plan.monthly_price > 0:
            raise BadRequestException(
                "This workspace already has a paid subscription. Use the billing portal to change or cancel the plan."
            )

        allow_trial = subscription is None or subscription.trial_used_at is None
        session = await self.provider.create_checkout_session(
            workspace_id=str(workspace_id),
            user_id=str(user_id),
            email=email,
            plan_code=normalized_code,
            customer_id=subscription.provider_customer_id if subscription else None,
            allow_trial=allow_trial,
        )

        if isinstance(self.provider, MockBillingProvider):
            now = datetime.now(timezone.utc)
            if subscription is None:
                subscription = Subscription(
                    workspace_id=workspace_id,
                    plan_id=plan.id,
                )
            plan_changed = subscription.plan_id != plan.id
            subscription.plan_id = plan.id
            subscription.provider = "MOCK"
            subscription.provider_subscription_id = f"mock_sub_{workspace_id}"
            subscription.provider_customer_id = f"mock_customer_{workspace_id}"
            subscription.provider_price_id = self.provider.price_id_for_plan(normalized_code)
            subscription.cancel_at_period_end = False
            subscription.current_period_start = now
            subscription.current_period_end = now + timedelta(days=30)
            if allow_trial and settings.STRIPE_TRIAL_DAYS > 0:
                subscription.status = SubscriptionStatus.TRIALING
                subscription.trial_end = now + timedelta(days=settings.STRIPE_TRIAL_DAYS)
                subscription.trial_used_at = now
            else:
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.trial_end = None
            await self.repository.flush_and_refresh_subscription(subscription)
            if plan_changed:
                await self.repository.allocate_credits(
                    workspace_id,
                    plan.included_credits,
                    f"{plan.name} plan activation",
                )
            await self.repository.db.commit()

        return session

    async def create_portal_session(self, workspace_id: UUID) -> BillingSession:
        subscription = await self.repository.get_subscription(workspace_id)
        if subscription is None or not subscription.provider_customer_id:
            raise BadRequestException("No billing customer exists for this workspace")
        return await self.provider.create_portal_session(
            customer_id=subscription.provider_customer_id
        )

    async def handle_webhook(self, payload: bytes, signature: str | None) -> bool:
        if not isinstance(self.provider, StripeBillingProvider):
            raise BadRequestException("Stripe billing is not enabled")
        event = self.provider.verify_webhook(payload, signature)
        event_id = str(event["id"])
        event_type = str(event["type"])

        claimed = await self.repository.claim_webhook_event(
            "STRIPE", event_id, event_type
        )
        if not claimed:
            return True

        try:
            data = self._mapping(event.get("data"))
            obj = self._mapping(data.get("object"))

            if event_type == "checkout.session.completed":
                subscription_id = self._string_id(obj.get("subscription"))
                if subscription_id:
                    remote = await self.provider.retrieve_subscription(subscription_id)
                    subscription, _, trial_started = await self._sync_remote_subscription(remote)
                    if trial_started:
                        await self._allocate_plan_credits(
                            subscription, "Stripe trial activation"
                        )

            elif event_type in {
                "customer.subscription.created",
                "customer.subscription.updated",
                "customer.subscription.deleted",
            }:
                subscription, _, trial_started = await self._sync_remote_subscription(obj)
                if trial_started:
                    await self._allocate_plan_credits(
                        subscription, "Stripe trial activation"
                    )

            elif event_type == "invoice.paid":
                subscription_id = self._invoice_subscription_id(obj)
                billing_reason = str(obj.get("billing_reason") or "")
                if subscription_id:
                    remote = await self.provider.retrieve_subscription(subscription_id)
                    subscription, _, _ = await self._sync_remote_subscription(remote)
                    if (
                        subscription.status == SubscriptionStatus.ACTIVE
                        and billing_reason in {"subscription_create", "subscription_cycle"}
                    ):
                        await self._allocate_plan_credits(
                            subscription,
                            f"Stripe invoice paid: {obj.get('id', 'invoice')}",
                        )

            elif event_type == "invoice.payment_failed":
                subscription_id = self._invoice_subscription_id(obj)
                if subscription_id:
                    subscription = await self.repository.get_subscription_by_provider_id(
                        subscription_id
                    )
                    if subscription is not None:
                        subscription.status = SubscriptionStatus.PAST_DUE
                        await self.repository.flush_and_refresh_subscription(subscription)

            await self.repository.db.commit()
        except Exception:
            await self.repository.db.rollback()
            raise
        return False

    async def _allocate_plan_credits(self, subscription: Subscription, description: str) -> None:
        plan = await self.repository.get_plan_by_code(
            self.provider.plan_code_for_price(subscription.provider_price_id) or ""
        )
        if plan is None:
            plan = subscription.plan
        if plan is not None and plan.included_credits > 0:
            await self.repository.allocate_credits(
                subscription.workspace_id,
                plan.included_credits,
                description,
            )

    async def _sync_remote_subscription(
        self,
        remote: dict[str, Any],
    ) -> tuple[Subscription, bool, bool]:
        provider_subscription_id = self._string_id(remote.get("id"))
        if not provider_subscription_id:
            raise BadRequestException("Invalid Stripe subscription payload")

        metadata = self._mapping(remote.get("metadata"))
        customer_id = self._string_id(remote.get("customer"))
        subscription = await self.repository.get_subscription_by_provider_id(
            provider_subscription_id
        )
        if subscription is None and customer_id:
            subscription = await self.repository.get_subscription_by_customer_id(customer_id)

        workspace_id: UUID | None = None
        raw_workspace_id = metadata.get("workspace_id")
        if raw_workspace_id:
            try:
                workspace_id = UUID(str(raw_workspace_id))
            except ValueError as exc:
                raise BadRequestException("Invalid Stripe subscription metadata") from exc
        elif subscription is not None:
            workspace_id = subscription.workspace_id
        if workspace_id is None:
            raise BadRequestException("Stripe subscription is missing workspace metadata")
        if subscription is not None and subscription.workspace_id != workspace_id:
            raise BadRequestException("Stripe subscription workspace mismatch")

        if subscription is None:
            subscription = await self.repository.get_subscription(workspace_id)

        price_id = self._subscription_price_id(remote)
        plan_code = str(metadata.get("plan_code") or "").upper()
        if not plan_code:
            plan_code = self.provider.plan_code_for_price(price_id) or ""
        plan = await self.repository.get_plan_by_code(plan_code)
        if plan is None:
            raise BadRequestException("Stripe subscription references an unknown plan")

        if subscription is None:
            subscription = Subscription(workspace_id=workspace_id, plan_id=plan.id)
        plan_changed = subscription.plan_id != plan.id

        status_value = str(remote.get("status") or "").lower()
        mapped_status = self._map_status(status_value)
        trial_started = (
            mapped_status == SubscriptionStatus.TRIALING
            and subscription.trial_used_at is None
        )

        subscription.workspace_id = workspace_id
        subscription.plan_id = plan.id
        subscription.status = mapped_status
        subscription.provider = "STRIPE"
        subscription.provider_subscription_id = provider_subscription_id
        subscription.provider_customer_id = customer_id
        subscription.provider_price_id = price_id
        subscription.cancel_at_period_end = bool(remote.get("cancel_at_period_end", False))
        subscription.current_period_start = self._subscription_period(remote, "current_period_start")
        subscription.current_period_end = self._subscription_period(remote, "current_period_end")
        subscription.trial_end = self._from_unix(remote.get("trial_end"))
        if trial_started:
            subscription.trial_used_at = datetime.now(timezone.utc)

        await self.repository.flush_and_refresh_subscription(subscription)
        return subscription, plan_changed, trial_started

    @staticmethod
    def _mapping(value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        try:
            return dict(value)
        except (TypeError, ValueError):
            return {}

    @classmethod
    def _string_id(cls, value: Any) -> str | None:
        if isinstance(value, str):
            return value
        mapping = cls._mapping(value)
        object_id = mapping.get("id")
        return object_id if isinstance(object_id, str) else None

    @classmethod
    def _subscription_price_id(cls, remote: dict[str, Any]) -> str | None:
        items = cls._mapping(remote.get("items"))
        rows = items.get("data") or []
        if not isinstance(rows, list) or not rows:
            return None
        first = cls._mapping(rows[0])
        price = cls._mapping(first.get("price"))
        return cls._string_id(price)

    @classmethod
    def _subscription_period(cls, remote: dict[str, Any], key: str) -> datetime | None:
        direct = cls._from_unix(remote.get(key))
        if direct is not None:
            return direct
        items = cls._mapping(remote.get("items"))
        rows = items.get("data") or []
        if isinstance(rows, list) and rows:
            return cls._from_unix(cls._mapping(rows[0]).get(key))
        return None

    @classmethod
    def _invoice_subscription_id(cls, invoice: dict[str, Any]) -> str | None:
        direct = cls._string_id(invoice.get("subscription"))
        if direct:
            return direct
        parent = cls._mapping(invoice.get("parent"))
        details = cls._mapping(parent.get("subscription_details"))
        return cls._string_id(details.get("subscription"))

    @staticmethod
    def _from_unix(value: Any) -> datetime | None:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        return None

    @staticmethod
    def _map_status(status: str) -> SubscriptionStatus:
        if status == "active":
            return SubscriptionStatus.ACTIVE
        if status == "trialing":
            return SubscriptionStatus.TRIALING
        if status in {"canceled", "incomplete_expired"}:
            return SubscriptionStatus.CANCELED
        return SubscriptionStatus.PAST_DUE
