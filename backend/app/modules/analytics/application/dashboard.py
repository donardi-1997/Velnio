from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credit import CreditWallet
from app.models.landing import LandingPage
from app.models.product import Product, ProductStatus
from app.schemas.dashboard import DashboardSummary


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def summary(self, workspace_id: UUID) -> DashboardSummary:
        products_result = await self.db.execute(
            select(func.count(Product.id)).where(Product.workspace_id == workspace_id)
        )
        analyzed_result = await self.db.execute(
            select(func.count(Product.id)).where(
                Product.workspace_id == workspace_id,
                Product.status.in_([ProductStatus.ANALYZED, ProductStatus.READY, ProductStatus.PUBLISHED]),
            )
        )
        landings_result = await self.db.execute(
            select(func.count(LandingPage.id)).join(Product).where(Product.workspace_id == workspace_id)
        )
        published_result = await self.db.execute(
            select(func.count(Product.id)).where(
                Product.workspace_id == workspace_id,
                Product.status == ProductStatus.PUBLISHED,
            )
        )
        wallet_result = await self.db.execute(
            select(CreditWallet).where(CreditWallet.workspace_id == workspace_id)
        )
        wallet = wallet_result.scalar_one_or_none()

        return DashboardSummary(
            total_products=products_result.scalar() or 0,
            analyzed_products=analyzed_result.scalar() or 0,
            total_landings=landings_result.scalar() or 0,
            published_products=published_result.scalar() or 0,
            credits_remaining=wallet.balance if wallet else 0,
        )
