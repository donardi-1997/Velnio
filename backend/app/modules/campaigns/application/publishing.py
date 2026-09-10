from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.logging import get_logger
from app.models.angle import SellingAngle
from app.models.campaign import Campaign, CampaignStatus
from app.models.landing import LandingPage
from app.models.offer import Offer
from app.models.product import Product, ProductImage
from app.models.store import Store
from app.models.visual_direction import CampaignVisualDirection
from app.services.shopify import get_shopify_provider

logger = get_logger(__name__)


class CampaignPublishingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_campaign(self, campaign_id: UUID, workspace_id: UUID) -> Campaign:
        result = await self.db.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.workspace_id == workspace_id,
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise NotFoundException("Campaign")
        return campaign

    async def readiness(self, campaign_id: UUID, workspace_id: UUID) -> dict:
        campaign = await self._get_campaign(campaign_id, workspace_id)

        product = None
        if campaign.product_id:
            result = await self.db.execute(select(Product).where(Product.id == campaign.product_id))
            product = result.scalar_one_or_none()

        store = None
        if campaign.store_id:
            result = await self.db.execute(select(Store).where(Store.id == campaign.store_id))
            store = result.scalar_one_or_none()

        result = await self.db.execute(
            select(SellingAngle).where(
                SellingAngle.campaign_id == campaign_id,
                SellingAngle.selected == True,
            )
        )
        angle = result.scalar_one_or_none()

        result = await self.db.execute(select(Offer).where(Offer.campaign_id == campaign_id))
        offer = result.scalar_one_or_none()

        result = await self.db.execute(select(LandingPage).where(LandingPage.campaign_id == campaign_id))
        landing = result.scalar_one_or_none()

        images = []
        if campaign.product_id:
            result = await self.db.execute(
                select(ProductImage).where(ProductImage.product_id == campaign.product_id)
            )
            images = result.scalars().all()

        result = await self.db.execute(
            select(CampaignVisualDirection).where(CampaignVisualDirection.campaign_id == campaign_id)
        )
        has_visual_direction = result.scalar_one_or_none() is not None

        checks = []

        def add_check(name: str, passed: bool, message: str) -> None:
            checks.append({"check": name, "status": "passed" if passed else "failed", "message": message})

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

        return {"ready": all(item["status"] == "passed" for item in checks), "checks": checks}

    async def publish(self, campaign_id: UUID, workspace_id: UUID) -> dict:
        campaign = await self._get_campaign(campaign_id, workspace_id)

        result = await self.db.execute(select(Product).where(Product.id == campaign.product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundException("Product")

        store = None
        if campaign.store_id:
            result = await self.db.execute(select(Store).where(Store.id == campaign.store_id))
            store = result.scalar_one_or_none()

        result = await self.db.execute(
            select(SellingAngle).where(
                SellingAngle.campaign_id == campaign_id,
                SellingAngle.selected == True,
            )
        )
        angle = result.scalar_one_or_none()

        result = await self.db.execute(select(LandingPage).where(LandingPage.campaign_id == campaign_id))
        landing = result.scalar_one_or_none()

        result = await self.db.execute(select(Offer).where(Offer.campaign_id == campaign_id))
        offer = result.scalar_one_or_none()

        try:
            publish_result = await get_shopify_provider().publish_campaign(
                campaign, product, store, angle, landing, offer
            )
            await self.db.execute(
                sa_update(Campaign).where(Campaign.id == campaign_id).values(
                    status=CampaignStatus.PUBLISHED,
                    external_product_id=publish_result.get("shopify_product_id"),
                    external_page_id=publish_result.get("shopify_page_id"),
                    published_at=datetime.now(timezone.utc),
                    last_publish_error=None,
                )
            )
            await self.db.flush()
            return {
                "status": "published",
                "provider": publish_result.get("provider", "mock"),
                "shopify_product_id": publish_result.get("shopify_product_id"),
                "shopify_page_id": publish_result.get("shopify_page_id"),
            }
        except Exception as exc:
            logger.error(f"Publish failed: {exc}")
            await self.db.execute(
                sa_update(Campaign).where(Campaign.id == campaign_id).values(
                    status=CampaignStatus.FAILED,
                    last_publish_error=str(exc)[:500],
                )
            )
            await self.db.flush()
            raise BadRequestException(f"Publish failed: {str(exc)[:200]}")
