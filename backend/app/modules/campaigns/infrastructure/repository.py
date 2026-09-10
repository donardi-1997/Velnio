from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.campaigns.domain import Campaign


class CampaignRepository:
    """Persistence boundary for campaign aggregate access."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[Campaign]:
        result = await self.db.execute(
            select(Campaign)
            .where(Campaign.workspace_id == workspace_id)
            .order_by(Campaign.created_at.desc())
        )
        return result.scalars().all()

    async def get_for_workspace(self, campaign_id: UUID, workspace_id: UUID) -> Campaign | None:
        result = await self.db.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_product(self, product_id: UUID, workspace_id: UUID) -> Sequence[Campaign]:
        result = await self.db.execute(
            select(Campaign)
            .where(
                Campaign.product_id == product_id,
                Campaign.workspace_id == workspace_id,
            )
            .order_by(Campaign.created_at.desc())
        )
        return result.scalars().all()

    async def add(self, campaign: Campaign) -> Campaign:
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign

    async def delete(self, campaign: Campaign) -> None:
        await self.db.delete(campaign)
        await self.db.flush()

    async def flush_and_refresh(self, campaign: Campaign) -> Campaign:
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign
