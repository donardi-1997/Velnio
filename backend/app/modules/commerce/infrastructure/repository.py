from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store


class StoreRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[Store]:
        result = await self.db.execute(select(Store).where(Store.workspace_id == workspace_id))
        return result.scalars().all()

    async def get_for_workspace(self, store_id: UUID, workspace_id: UUID) -> Store | None:
        result = await self.db.execute(
            select(Store).where(Store.id == store_id, Store.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def add(self, store: Store) -> Store:
        self.db.add(store)
        await self.db.flush()
        await self.db.refresh(store)
        return store

    async def flush_and_refresh(self, store: Store) -> Store:
        await self.db.flush()
        await self.db.refresh(store)
        return store
