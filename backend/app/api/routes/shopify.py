from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.product import Product, ProductStatus
from app.models.store import Store, StoreStatus
from app.schemas.store import StoreResponse
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.shopify import get_shopify_provider
from uuid import UUID

router = APIRouter()


@router.post("/{product_id}/publish", status_code=200)
async def publish_product(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundException("Product")

    store = None
    if product.store_id:
        store_result = await db.execute(select(Store).where(Store.id == product.store_id))
        store = store_result.scalar_one_or_none()

    provider = get_shopify_provider()
    publish_result = await provider.publish_product(product, store)

    product.status = ProductStatus.PUBLISHED
    product.published_product_id = publish_result.get("shopify_product_id")
    await db.flush()
    await db.refresh(product)

    return {
        "status": "published",
        "provider": publish_result.get("provider", "mock"),
        "shopify_product_id": publish_result.get("shopify_product_id"),
        "shopify_page_id": publish_result.get("shopify_page_id"),
    }
