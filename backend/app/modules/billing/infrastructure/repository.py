from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credit import CreditTransaction, CreditWallet
from app.models.plan import Plan
from app.models.subscription import Subscription


class BillingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_wallet(self, workspace_id: UUID) -> CreditWallet | None:
        result = await self.db.execute(
            select(CreditWallet).where(CreditWallet.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def list_transactions(self, workspace_id: UUID, limit: int = 50) -> Sequence[CreditTransaction]:
        result = await self.db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.workspace_id == workspace_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def list_active_plans(self) -> Sequence[Plan]:
        result = await self.db.execute(select(Plan).where(Plan.active == True))
        return result.scalars().all()

    async def get_subscription(self, workspace_id: UUID) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(Subscription.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()
