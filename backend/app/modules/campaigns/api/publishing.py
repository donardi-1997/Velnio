from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.angle import SellingAngle
from app.models.campaign import Campaign, CampaignStatus
from app.models.landing import LandingPage
from app.models.offer import Offer
from app.models.product import Product
from app.models.store import Store
from app.models.workspace import Workspace
from app.services.shopify import get_shopify_provider

logger = get_logger(__name__)
router = APIRouter()


@router.post("/{campaign_id}/publish")
async def publish_campaign(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign")

    product_result = await db.execute(select(Product).where(Product.id == campaign.product_id))
    product = product_result.scalar_one_or_none()
    if not product:
        raise NotFoundException("Product")

    store = None
    if campaign.store_id:
        store_result = await db.execute(select(Store).where(Store.id == campaign.store_id))
        store = store_result.scalar_one_or_none()

    angle_result = await db.execute(
        select(SellingAngle).where(SellingAngle.campaign_id == campaign_id, SellingAngle.selected == True)
    )
    angle = angle_result.scalar_one_or_none()

    landing_result = await db.execute(select(LandingPage).where(LandingPage.campaign_id == campaign_id))
    landing = landing_result.scalar_one_or_none()

    offer_result = await db.execute(select(Offer).where(Offer.campaign_id == campaign_id))
    offer = offer_result.scalar_one_or_none()

    try:
        publish_result = await get_shopify_provider().publish_campaign(
            campaign, product, store, angle, landing, offer
        )
        await db.execute(
            sa_update(Campaign).where(Campaign.id == campaign_id).values(
                status=CampaignStatus.PUBLISHED,
                external_product_id=publish_result.get("shopify_product_id"),
                external_page_id=publish_result.get("shopify_page_id"),
                published_at=datetime.now(timezone.utc),
                last_publish_error=None,
            )
        )
        await db.flush()
        return {
            "status": "published",
            "provider": publish_result.get("provider", "mock"),
            "shopify_product_id": publish_result.get("shopify_product_id"),
            "shopify_page_id": publish_result.get("shopify_page_id"),
        }
    except Exception as exc:
        logger.error(f"Publish failed: {exc}")
        await db.execute(
            sa_update(Campaign).where(Campaign.id == campaign_id).values(
                status=CampaignStatus.FAILED,
                last_publish_error=str(exc)[:500],
            )
        )
        await db.flush()
        raise BadRequestException(f"Publish failed: {str(exc)[:200]}")
