from datetime import datetime, timezone
import secrets
from uuid import UUID

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException, BadGatewayException, NotFoundException
from app.core.logging import get_logger
from app.models.angle import SellingAngle
from app.models.campaign import Campaign, CampaignStatus
from app.models.landing import LandingPage
from app.models.offer import Offer
from app.models.product import Product, ProductImage
from app.models.store import Store, StoreStatus
from app.models.tracking import LandingVariant
from app.models.visual_direction import CampaignVisualDirection
from app.modules.commerce.application.shopify_connection import ShopifyConnectionService
from app.services.shopify import get_shopify_provider
from app.services.shopify.real_provider import RealShopifyProvider
from app.services.shopify.webhooks import ShopifyWebhookRegistrar, get_public_api_origin

logger = get_logger(__name__)


class CampaignPublishingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.shopify_connection = ShopifyConnectionService(db)

    async def _get_campaign(
        self,
        campaign_id: UUID,
        workspace_id: UUID,
        *,
        for_update: bool = False,
    ) -> Campaign:
        statement = select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.workspace_id == workspace_id,
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.db.execute(statement)
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise NotFoundException("Campaign")
        return campaign

    async def _get_product(self, product_id: UUID | None, workspace_id: UUID) -> Product | None:
        if product_id is None:
            return None
        result = await self.db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_store(self, store_id: UUID | None, workspace_id: UUID) -> Store | None:
        if store_id is None:
            return None
        result = await self.db.execute(
            select(Store).where(
                Store.id == store_id,
                Store.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def _prepare_storefront_tracking(
        self,
        campaign: Campaign,
        landing: LandingPage | None,
        angle: SellingAngle | None,
        offer: Offer | None,
    ) -> None:
        if landing is None:
            return
        if not campaign.tracking_key:
            campaign.tracking_key = secrets.token_urlsafe(32)

        result = await self.db.execute(
            select(LandingVariant).where(
                LandingVariant.campaign_id == campaign.id,
                LandingVariant.variant_key == "A",
            )
        )
        control = result.scalar_one_or_none()
        if control is None:
            all_result = await self.db.execute(
                select(LandingVariant).where(LandingVariant.campaign_id == campaign.id)
            )
            existing_variants = all_result.scalars().all()
            has_existing_traffic = any(
                float(item.traffic_weight or 0) > 0 for item in existing_variants
            )
            control = LandingVariant(
                campaign_id=campaign.id,
                name="Control",
                variant_key="A",
                status="PAUSED" if has_existing_traffic else "ACTIVE",
                traffic_weight=0 if has_existing_traffic else 100,
                landing_page_id=landing.id,
                selling_angle_id=angle.id if angle else landing.selling_angle_id,
                offer_id=offer.id if offer else None,
            )
            self.db.add(control)
            await self.db.flush()
        else:
            control.landing_page_id = landing.id
            if angle:
                control.selling_angle_id = angle.id
            if offer:
                control.offer_id = offer.id

        variants_result = await self.db.execute(
            select(LandingVariant)
            .where(
                LandingVariant.campaign_id == campaign.id,
                LandingVariant.status == "ACTIVE",
                LandingVariant.traffic_weight > 0,
            )
            .order_by(LandingVariant.variant_key)
        )
        active_variants = list(variants_result.scalars().all())
        if not active_variants:
            control.status = "ACTIVE"
            control.traffic_weight = 100
            active_variants = [control]

        landing_ids = {
            item.landing_page_id for item in active_variants if item.landing_page_id is not None
        }
        pages_by_id: dict[UUID, LandingPage] = {}
        if landing_ids:
            pages_result = await self.db.execute(
                select(LandingPage).where(LandingPage.id.in_(landing_ids))
            )
            pages_by_id = {page.id: page for page in pages_result.scalars().all()}

        landing._velnio_tracking = {
            "endpoint": (
                f"{get_public_api_origin()}/api/tracking/beacon/{campaign.tracking_key}"
            ),
            "tracking_key": campaign.tracking_key,
            "campaign_id": str(campaign.id),
            "product_handle": RealShopifyProvider._stable_handle("campaign", campaign.id),
        }
        landing._velnio_experiment_variants = [
            (item, pages_by_id.get(item.landing_page_id) or landing)
            for item in active_variants
        ]
        await self.db.flush()

    async def readiness(self, campaign_id: UUID, workspace_id: UUID) -> dict:
        campaign = await self._get_campaign(campaign_id, workspace_id)
        product = await self._get_product(campaign.product_id, workspace_id)
        store = await self._get_store(campaign.store_id, workspace_id)

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
        if campaign.product_id and product is not None:
            result = await self.db.execute(
                select(ProductImage).where(
                    ProductImage.product_id == campaign.product_id,
                )
            )
            images = result.scalars().all()

        result = await self.db.execute(
            select(CampaignVisualDirection).where(CampaignVisualDirection.campaign_id == campaign_id)
        )
        has_visual_direction = result.scalar_one_or_none() is not None

        checks = []

        def add_check(name: str, passed: bool, message: str) -> None:
            checks.append({"check": name, "status": "passed" if passed else "failed", "message": message})

        store_connected = store is not None and store.status == StoreStatus.CONNECTED
        add_check(
            "store_connected",
            store_connected,
            "Store connected" if store_connected else "No connected store",
        )
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
        campaign = await self._get_campaign(campaign_id, workspace_id, for_update=True)

        if campaign.status == CampaignStatus.PUBLISHED and campaign.external_product_id:
            return {
                "status": "published",
                "provider": "existing",
                "shopify_product_id": campaign.external_product_id,
                "shopify_page_id": campaign.external_page_id,
            }

        product = await self._get_product(campaign.product_id, workspace_id)
        if not product:
            raise NotFoundException("Product")

        store = await self._get_store(campaign.store_id, workspace_id)
        if campaign.store_id and store is None:
            raise NotFoundException("Store")
        if store is not None:
            store = await self.shopify_connection.ensure_valid_credentials(store)

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
            await self._prepare_storefront_tracking(campaign, landing, angle, offer)
            provider = get_shopify_provider()
            if isinstance(provider, RealShopifyProvider) and store is not None:
                await ShopifyWebhookRegistrar().ensure_orders_create(store)
            publish_result = await provider.publish_campaign(
                campaign, product, store, angle, landing, offer
            )
            shopify_product_id = publish_result.get("shopify_product_id")
            if not shopify_product_id:
                raise BadGatewayException("Shopify did not return a product identifier")

            await self.db.execute(
                sa_update(Campaign).where(
                    Campaign.id == campaign_id,
                    Campaign.workspace_id == workspace_id,
                ).values(
                    status=CampaignStatus.PUBLISHED,
                    external_product_id=str(shopify_product_id),
                    external_page_id=publish_result.get("shopify_page_id"),
                    external_page_handle=publish_result.get("shopify_page_handle"),
                    external_page_url=publish_result.get("shopify_page_url"),
                    published_at=datetime.now(timezone.utc),
                    last_publish_error=None,
                )
            )
            await self.db.flush()
            return {
                "status": "published",
                "provider": publish_result.get("provider", "mock"),
                "shopify_product_id": str(shopify_product_id),
                "shopify_page_id": publish_result.get("shopify_page_id"),
            }
        except AppException as exc:
            await self._mark_failed(campaign_id, workspace_id, exc.detail)
            raise
        except Exception as exc:
            logger.error("Shopify campaign publish failed: %s", type(exc).__name__)
            safe_message = "Shopify publish failed; try again"
            await self._mark_failed(campaign_id, workspace_id, safe_message)
            raise BadGatewayException(safe_message) from exc

    async def _mark_failed(self, campaign_id: UUID, workspace_id: UUID, message: str) -> None:
        await self.db.execute(
            sa_update(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.workspace_id == workspace_id,
            ).values(
                status=CampaignStatus.FAILED,
                last_publish_error=str(message)[:500],
            )
        )
        await self.db.flush()
