from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[Product]:
        result = await self.db.execute(
            select(Product).where(Product.workspace_id == workspace_id).order_by(Product.created_at.desc())
        )
        return result.scalars().all()

    async def get_for_workspace(self, product_id: UUID, workspace_id: UUID) -> Product | None:
        result = await self.db.execute(
            select(Product).where(Product.id == product_id, Product.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def add(self, product: Product) -> Product:
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def flush_and_refresh(self, product: Product) -> Product:
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def delete(self, product: Product) -> None:
        await self.db.delete(product)
        await self.db.flush()
