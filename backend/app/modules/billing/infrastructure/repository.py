from __future__ import annotations

from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.plan import Plan
from app.models.product import Product
from app.models.store import Store, StoreStatus
from app.models.subscription import BillingWebhookEvent, Subscription


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

    async def get_plan_by_code(self, code: str) -> Plan | None:
        result = await self.db.execute(
            select(Plan).where(Plan.code == code.upper(), Plan.active == True)
        )
        return result.scalar_one_or_none()

    async def get_subscription(self, workspace_id: UUID) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def get_subscription_by_provider_id(self, provider_subscription_id: str) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.provider_subscription_id == provider_subscription_id)
        )
        return result.scalar_one_or_none()

    async def get_subscription_by_customer_id(self, provider_customer_id: str) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.provider_customer_id == provider_customer_id)
        )
        return result.scalar_one_or_none()

    async def flush_and_refresh_subscription(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        await self.db.flush()
        await self.db.refresh(subscription)
        return subscription

    async def claim_webhook_event(
        self,
        provider: str,
        provider_event_id: str,
        event_type: str,
    ) -> bool:
        """Claim a provider event inside the current transaction.

        The unique constraint serializes concurrent deliveries. If another
        transaction commits the same event first, the insert raises and this
        delivery becomes a no-op. If the first transaction rolls back, the
        waiting insert can succeed and safely process the event.
        """
        self.db.add(
            BillingWebhookEvent(
                provider=provider,
                provider_event_id=provider_event_id,
                event_type=event_type,
            )
        )
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            return False
        return True

    async def count_active_stores(self, workspace_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(Store.id)).where(
                Store.workspace_id == workspace_id,
                Store.status != StoreStatus.DISCONNECTED,
            )
        )
        return int(result.scalar_one())

    async def count_products_created_between(
        self,
        workspace_id: UUID,
        start: datetime,
        end: datetime,
    ) -> int:
        result = await self.db.execute(
            select(func.count(Product.id)).where(
                Product.workspace_id == workspace_id,
                Product.created_at >= start,
                Product.created_at < end,
            )
        )
        return int(result.scalar_one())

    async def allocate_credits(
        self,
        workspace_id: UUID,
        amount: int,
        description: str,
    ) -> None:
        wallet = await self.get_wallet(workspace_id)
        if wallet is None:
            wallet = CreditWallet(
                workspace_id=workspace_id,
                balance=0,
                lifetime_credits=0,
            )
            self.db.add(wallet)
            await self.db.flush()
        wallet.balance += amount
        wallet.lifetime_credits += amount
        self.db.add(
            CreditTransaction(
                workspace_id=workspace_id,
                wallet_id=wallet.id,
                amount=amount,
                transaction_type=TransactionType.ALLOCATION,
                description=description,
                reference_type="billing",
            )
        )
        await self.db.flush()
