from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.product import Product, ProductImage
from app.models.store import Store
from app.models.campaign import Campaign
from app.models.angle import SellingAngle
from app.models.landing import LandingPage
from app.models.offer import Offer
from app.models.visual_direction import CampaignVisualDirection
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from uuid import UUID

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
        img_result = await db.execute(
            select(ProductImage).where(ProductImage.product_id == campaign.product_id)
        )
        images = img_result.scalars().all()

    vd_result = await db.execute(select(CampaignVisualDirection).where(CampaignVisualDirection.campaign_id == campaign_id))
    has_visual_direction = vd_result.scalar_one_or_none() is not None

    checks = []
    def _check(name, passed, message=""):
        checks.append({
            "check": name,
            "status": "passed" if passed else "failed",
            "message": message or (f"{name} OK" if passed else f"{name} missing"),
        })

    _check("store_connected", store is not None, "Store connected" if store else "No store connected")
    _check("product_exists", product is not None, "Product exists" if product else "No product")
    _check("angle_selected", angle is not None, "Angle selected" if angle else "No angle selected")
    _check("offer_exists", offer is not None, "Offer exists" if offer else "No offer")
    _check("landing_ready", landing is not None, "Landing ready" if landing else "Landing not ready")
    _check("has_images", bool(images), f"{len(images)} images" if images else "No images")
    _check("has_visual_direction", has_visual_direction, "Visual direction set" if has_visual_direction else "No visual direction")

    prices_ok = bool(campaign.selling_price and campaign.supplier_price)
    _check("prices_set", prices_ok, "Prices set" if prices_ok else "Prices not set")

    ready = all(c["status"] == "passed" for c in checks)

    return {"ready": ready, "checks": checks}
