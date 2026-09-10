from __future__ import annotations

from typing import Sequence
from uuid import UUID

from app.core.exceptions import NotFoundException
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.modules.billing.infrastructure.repository import BillingRepository


class SubscriptionService:
    def __init__(self, repository: BillingRepository) -> None:
        self.repository = repository

    async def list_plans(self) -> Sequence[Plan]:
        return await self.repository.list_active_plans()

    async def get_subscription(self, workspace_id: UUID) -> Subscription:
        subscription = await self.repository.get_subscription(workspace_id)
        if subscription is None:
            raise NotFoundException("Subscription")
        return subscription
