from typing import Sequence
from uuid import UUID

from app.core.exceptions import NotFoundException
from app.models.product import Product
from app.modules.catalog.infrastructure.repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    async def list(self, workspace_id: UUID) -> Sequence[Product]:
        return await self.repository.list_for_workspace(workspace_id)

    async def get(self, product_id: UUID, workspace_id: UUID) -> Product:
        product = await self.repository.get_for_workspace(product_id, workspace_id)
        if not product:
            raise NotFoundException("Product")
        return product

    async def create(self, data: ProductCreate, workspace_id: UUID) -> Product:
        product = Product(
            workspace_id=workspace_id,
            name=data.name,
            source_type=data.source_type,
            source_url=data.source_url,
            supplier_price=data.supplier_price,
            selling_price=data.selling_price,
            currency=data.currency,
            description=data.description,
            target_country=data.target_country,
            target_language=data.target_language,
            store_id=data.store_id,
        )
        return await self.repository.add(product)

    async def update(self, product_id: UUID, data: ProductUpdate, workspace_id: UUID) -> Product:
        product = await self.get(product_id, workspace_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(product, key, value)
        return await self.repository.flush_and_refresh(product)

    async def delete(self, product_id: UUID, workspace_id: UUID) -> None:
        product = await self.get(product_id, workspace_id)
        await self.repository.delete(product)
