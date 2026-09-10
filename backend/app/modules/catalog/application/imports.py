from __future__ import annotations

from typing import Sequence
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.product import (
    ImagePurpose,
    ImageSourceType,
    Product,
    ProductImage,
    ProductStatus,
    SourceType,
)
from app.modules.billing.application.entitlements import EntitlementService
from app.modules.billing.infrastructure.repository import BillingRepository
from app.services.import_engine import import_product_from_url
from app.services.storage import get_storage_provider


class ProductImportService:
    """Application service for product import previews, creation and image uploads."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.entitlements = EntitlementService(BillingRepository(db))

    async def preview(self, url: str) -> dict:
        return await import_product_from_url(url)

    async def create(self, data, workspace_id: UUID) -> Product:
        await self.entitlements.assert_can_create_product(workspace_id)
        product = Product(
            workspace_id=workspace_id,
            store_id=data.store_id,
            name=data.name,
            description=data.description,
            selling_price=data.selling_price,
            supplier_price=data.supplier_price,
            currency=data.currency,
            source_type=SourceType(data.source_type),
            source_url=data.source_url,
            source_domain=data.source_domain,
            source_metadata=data.source_metadata,
            target_country=data.target_country,
            target_language=data.target_language,
            status=ProductStatus.DRAFT,
        )
        self.db.add(product)
        await self.db.flush()

        for image in data.images:
            self.db.add(
                ProductImage(
                    product_id=product.id,
                    image_url=image.url,
                    source_type=ImageSourceType.SOURCE,
                    purpose=ImagePurpose.ORIGINAL,
                    position=image.position,
                )
            )

        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def upload_images(
        self,
        product_id: UUID,
        files: Sequence[UploadFile],
        workspace_id: UUID,
    ) -> Product:
        result = await self.db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.workspace_id == workspace_id,
            )
        )
        product = result.scalar_one_or_none()
        if product is None:
            raise NotFoundException("Product")

        image_result = await self.db.execute(
            select(ProductImage).where(ProductImage.product_id == product_id)
        )
        existing_count = len(image_result.scalars().all())

        storage = get_storage_provider()
        max_size = settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024
        allowed_types = {"image/jpeg", "image/png", "image/webp"}

        for index, file in enumerate(files):
            if file.content_type not in allowed_types:
                raise BadRequestException(
                    f"Invalid file type: {file.content_type}. Allowed: JPEG, PNG, WEBP"
                )

            content = await file.read()
            if len(content) > max_size:
                raise BadRequestException(
                    f"File too large: {file.filename}. Max size: {settings.MAX_IMAGE_UPLOAD_MB}MB"
                )

            key = await storage.save_bytes(
                content,
                file.content_type,
                f"products/{product_id}",
            )
            url = storage.get_public_url(key)
            self.db.add(
                ProductImage(
                    product_id=product.id,
                    image_url=url,
                    storage_key=key,
                    source_type=ImageSourceType.UPLOADED,
                    purpose=ImagePurpose.ORIGINAL,
                    position=existing_count + index,
                )
            )

        await self.db.flush()
        await self.db.refresh(product)
        return product
