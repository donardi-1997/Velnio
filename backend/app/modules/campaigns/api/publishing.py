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
from app.models.product import Product, ProductImage
from app.models.store import Store
from app.models.visual_direction import CampaignVisualDirection
from app.models.workspace import Workspace
from app.services.shopify import get_shopify_provider

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{campaign_id}/publish-readiness")
async def publish_readiness(
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

    product = None
    if campaign.product_id:
        product_result = await db.execute(select(Product).where(Product.id == campaign.product_id))
        product = product_result.scalar_one_or_none()

    store = None
    if campaign.store_id:
        store_result = await db.execute(select(Store).where(Store.id == campaign.store_id))
        store = store_result.scalar_one_or_none()

    angle_result = await db.execute(
        select(SellingAngle).where(SellingAngle.campaign_id == campaign_id, SellingAngle.selected == True)
    )
    angle = angle_result.scalar_one_or_none()

    offer_result = await db.execute(select(Offer).where(Offer.campaign_id == campaign_id))
    offer = offer_result.scalar_one_or_none()

    landing_result = await db.execute(select(LandingPage).where(LandingPage.campaign_id == campaign_id))
    landing = landing_result.scalar_one_or_none()

    images = []
    if campaign.product_id:
        image_result = await db.execute(
            select(ProductImage).where(ProductImage.product_id == campaign.product_id)
        )
        images = image_result.scalars().all()

    direction_result = await db.execute(
        select(CampaignVisualDirection).where(CampaignVisualDirection.campaign_id == campaign_id)
    )
    has_visual_direction = direction_result.scalar_one_or_none() is not None

    checks = []

    def add_check(name: str, passed: bool, message: str = "") -> None:
        checks.append(
            {
                "check": name,
                "status": "passed" if passed else "failed",
                "message": message or (f"{name} OK" if passed else f"{name} missing"),
            }
        )

    add_check("store_connected", store is not None, "Store connected" if store else "No store connected")
    add_check("product_exists", product is not None, "Product exists" if product else "No product")
    add_check("angle_selected", angle is not None, "Angle selected" if angle else "No angle selected")
    add_check("offer_exists", offer is not None, "Offer exists" if offer else "No offer")
    add_check("landing_ready", landing is not None, "Landing ready" if landing else "Landing not ready")
    add_check("has_images", bool(images), f"{len(images)} images" if images else "No images")
    add_check(
        "has_visual_direction",
        has_visual_direction,
        "Visual direction set" if has_visual_direction else "No visual direction",
    )
    prices_ok = bool(campaign.selling_price and campaign.supplier_price)
    add_check("prices_set", prices_ok, "Prices set" if prices_ok else "Prices not set")

    return {
        "ready": all(check["status"] == "passed" for check in checks),
        "checks": checks,
    }


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
