from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, BadGatewayException, NotFoundException
from app.core.logging import get_logger
from app.models.product import Product, ProductStatus
from app.models.store import Store
from app.modules.commerce.application.shopify_connection import ShopifyConnectionService
from app.services.shopify import get_shopify_provider

logger = get_logger(__name__)


class ProductPublishingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.shopify_connection = ShopifyConnectionService(db)

    async def publish(self, product_id: UUID, workspace_id: UUID) -> dict:
        result = await self.db.execute(
            select(Product)
            .where(Product.id == product_id, Product.workspace_id == workspace_id)
            .with_for_update()
        )
        product = result.scalar_one_or_none()
        if product is None:
            raise NotFoundException("Product")

        if product.status == ProductStatus.PUBLISHED and product.published_product_id:
            return {
                "status": "published",
                "provider": "existing",
                "shopify_product_id": product.published_product_id,
                "shopify_page_id": None,
            }

        store = None
        if product.store_id:
            store_result = await self.db.execute(
                select(Store).where(
                    Store.id == product.store_id,
                    Store.workspace_id == workspace_id,
                )
            )
            store = store_result.scalar_one_or_none()
            if store is None:
                raise NotFoundException("Store")
            store = await self.shopify_connection.ensure_valid_credentials(store)

        try:
            publish_result = await get_shopify_provider().publish_product(product, store)
        except AppException:
            raise
        except Exception as exc:
            logger.error("Shopify product publish failed: %s", type(exc).__name__)
            raise BadGatewayException("Shopify publish failed; try again") from exc

        shopify_product_id = publish_result.get("shopify_product_id")
        if not shopify_product_id:
            raise BadGatewayException("Shopify did not return a product identifier")

        product.status = ProductStatus.PUBLISHED
        product.published_product_id = str(shopify_product_id)
        await self.db.flush()
        await self.db.refresh(product)

        return {
            "status": "published",
            "provider": publish_result.get("provider", "mock"),
            "shopify_product_id": str(shopify_product_id),
            "shopify_page_id": publish_result.get("shopify_page_id"),
        }
