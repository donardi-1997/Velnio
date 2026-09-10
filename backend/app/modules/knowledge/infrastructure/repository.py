from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeSource


class KnowledgeSourceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        workspace_id: UUID,
        *,
        product_id: UUID | None = None,
        campaign_id: UUID | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> Sequence[KnowledgeSource]:
        query = select(KnowledgeSource).where(KnowledgeSource.workspace_id == workspace_id)
        if product_id:
            query = query.where(KnowledgeSource.product_id == product_id)
        if campaign_id:
            query = query.where(KnowledgeSource.campaign_id == campaign_id)
        if source_type:
            query = query.where(KnowledgeSource.source_type == source_type)
        if status:
            query = query.where(KnowledgeSource.status == status)
        result = await self.db.execute(query.order_by(KnowledgeSource.created_at.desc()))
        return result.scalars().all()

    async def get(self, source_id: UUID, workspace_id: UUID) -> KnowledgeSource | None:
        result = await self.db.execute(
            select(KnowledgeSource).where(
                KnowledgeSource.id == source_id,
                KnowledgeSource.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_for_product(self, product_id: UUID, workspace_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(KnowledgeSource.id)).where(
                KnowledgeSource.workspace_id == workspace_id,
                KnowledgeSource.product_id == product_id,
            )
        )
        return result.scalar() or 0

    async def count_for_campaign(self, campaign_id: UUID, workspace_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(KnowledgeSource.id)).where(
                KnowledgeSource.workspace_id == workspace_id,
                KnowledgeSource.campaign_id == campaign_id,
            )
        )
        return result.scalar() or 0

    async def add(self, source: KnowledgeSource) -> KnowledgeSource:
        self.db.add(source)
        await self.db.flush()
        await self.db.refresh(source)
        return source

    async def flush_and_refresh(self, source: KnowledgeSource) -> KnowledgeSource:
        await self.db.flush()
        await self.db.refresh(source)
        return source

    async def delete(self, source: KnowledgeSource) -> None:
        await self.db.delete(source)
        await self.db.flush()
