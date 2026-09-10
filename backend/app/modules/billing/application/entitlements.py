from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.core.exceptions import PlanLimitException
from app.models.plan import Plan
from app.models.subscription import SubscriptionStatus
from app.modules.billing.infrastructure.repository import BillingRepository


class EntitlementService:
    """Resolve the effective plan and enforce server-side usage limits."""

    def __init__(self, repository: BillingRepository) -> None:
        self.repository = repository

    async def effective_plan(self, workspace_id: UUID) -> tuple[Plan, str]:
        subscription = await self.repository.get_subscription(workspace_id)
        if (
            subscription is not None
            and subscription.status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}
            and subscription.plan is not None
        ):
            return subscription.plan, subscription.status.value

        free_plan = await self.repository.get_plan_by_code("FREE")
        if free_plan is None:
            raise PlanLimitException("No active plan is available for this workspace")
        status = subscription.status.value if subscription is not None else "NONE"
        return free_plan, status

    @staticmethod
    def _month_window(now: datetime | None = None) -> tuple[datetime, datetime]:
        current = now or datetime.now(timezone.utc)
        start = datetime(current.year, current.month, 1, tzinfo=timezone.utc)
        if current.month == 12:
            end = datetime(current.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(current.year, current.month + 1, 1, tzinfo=timezone.utc)
        return start, end

    async def snapshot(self, workspace_id: UUID) -> dict:
        plan, subscription_status = await self.effective_plan(workspace_id)
        month_start, month_end = self._month_window()
        stores_used = await self.repository.count_active_stores(workspace_id)
        products_used = await self.repository.count_products_created_between(
            workspace_id,
            month_start,
            month_end,
        )
        return {
            "plan_code": plan.code,
            "plan_name": plan.name,
            "subscription_status": subscription_status,
            "max_stores": plan.max_stores,
            "stores_used": stores_used,
            "max_products_per_month": plan.max_products_per_month,
            "products_used_this_month": products_used,
            "included_credits": plan.included_credits,
        }

    async def assert_can_add_store(self, workspace_id: UUID) -> None:
        plan, _ = await self.effective_plan(workspace_id)
        used = await self.repository.count_active_stores(workspace_id)
        if used >= plan.max_stores:
            raise PlanLimitException(
                f"Store limit reached for {plan.name}: {used}/{plan.max_stores}. Upgrade your plan to connect another store."
            )

    async def assert_can_create_product(self, workspace_id: UUID) -> None:
        plan, _ = await self.effective_plan(workspace_id)
        start, end = self._month_window()
        used = await self.repository.count_products_created_between(workspace_id, start, end)
        if used >= plan.max_products_per_month:
            raise PlanLimitException(
                f"Monthly product limit reached for {plan.name}: {used}/{plan.max_products_per_month}. Upgrade your plan to add more products."
            )
