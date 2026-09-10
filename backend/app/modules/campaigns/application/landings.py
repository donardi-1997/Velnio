from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BadGatewayException,
    BadRequestException,
    InsufficientCreditsException,
    NotFoundException,
)
from app.core.logging import get_logger
from app.models.analysis import ProductAnalysis
from app.models.angle import SellingAngle
from app.models.campaign import CampaignStatus
from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.landing import LandingPage, LandingSection, LandingStatus
from app.models.offer import Offer
from app.models.product import Product
from app.models.tracking import LandingVariant
from app.modules.campaigns.infrastructure import CampaignRepository
from app.services.ai import get_ai_provider

logger = get_logger(__name__)


class CampaignLandingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.campaigns = CampaignRepository(db)

    async def get(self, campaign_id: UUID, workspace_id: UUID) -> LandingPage:
        if await self.campaigns.get_for_workspace(campaign_id, workspace_id) is None:
            raise NotFoundException("Campaign")
        result = await self.db.execute(select(LandingPage).where(LandingPage.campaign_id == campaign_id))
        landing = result.scalar_one_or_none()
        if landing is None:
            raise NotFoundException("Landing page")
        return landing

    async def _get_control_variant(self, campaign_id: UUID) -> LandingVariant | None:
        result = await self.db.execute(
            select(LandingVariant).where(
                LandingVariant.campaign_id == campaign_id,
                LandingVariant.variant_key == "A",
            )
        )
        return result.scalar_one_or_none()

    async def _attach_control_variant(
        self,
        campaign_id: UUID,
        landing: LandingPage,
        angle: SellingAngle,
        offer: Offer | None,
    ) -> LandingVariant:
        control = await self._get_control_variant(campaign_id)
        if control is None:
            other_result = await self.db.execute(
                select(LandingVariant).where(LandingVariant.campaign_id == campaign_id)
            )
            has_experiment_traffic = any(
                float(item.traffic_weight or 0) > 0 for item in other_result.scalars().all()
            )
            control = LandingVariant(
                campaign_id=campaign_id,
                name="Control",
                variant_key="A",
                status="PAUSED" if has_experiment_traffic else "ACTIVE",
                traffic_weight=0 if has_experiment_traffic else 100,
            )
            self.db.add(control)

        control.landing_page_id = landing.id
        control.selling_angle_id = angle.id
        control.offer_id = offer.id if offer else None
        await self.db.flush()
        return control

    async def generate(self, campaign_id: UUID, workspace_id: UUID) -> LandingPage:
        campaign = await self.campaigns.get_for_workspace(campaign_id, workspace_id)
        if campaign is None:
            raise NotFoundException("Campaign")

        product_result = await self.db.execute(select(Product).where(Product.id == campaign.product_id))
        product = product_result.scalar_one_or_none()
        if product is None:
            raise NotFoundException("Product")

        angle_result = await self.db.execute(
            select(SellingAngle).where(SellingAngle.campaign_id == campaign_id, SellingAngle.selected == True)
        )
        angle = angle_result.scalar_one_or_none()
        if angle is None:
            raise BadRequestException("Please select a selling angle first")

        analysis_result = await self.db.execute(select(ProductAnalysis).where(ProductAnalysis.product_id == product.id))
        analysis = analysis_result.scalar_one_or_none()
        offer_result = await self.db.execute(select(Offer).where(Offer.campaign_id == campaign_id))
        offer = offer_result.scalar_one_or_none()

        wallet_result = await self.db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace_id))
        wallet = wallet_result.scalar_one_or_none()
        if wallet is None or wallet.balance < settings.PLAN_LANDING_COST:
            raise InsufficientCreditsException()

        existing_result = await self.db.execute(select(LandingPage).where(LandingPage.campaign_id == campaign_id))
        existing_landing = existing_result.scalar_one_or_none()
        if existing_landing:
            control = await self._get_control_variant(campaign_id)
            if control and control.landing_page_id == existing_landing.id:
                control.landing_page_id = None
            sections_result = await self.db.execute(
                select(LandingSection).where(LandingSection.landing_page_id == existing_landing.id)
            )
            for section in sections_result.scalars().all():
                await self.db.delete(section)
            await self.db.delete(existing_landing)
            await self.db.flush()

        try:
            landing_data = await get_ai_provider().generate_landing_for_campaign(
                product, campaign, angle, analysis, offer
            )
            landing = LandingPage(
                campaign_id=campaign_id,
                product_id=product.id,
                selling_angle_id=angle.id,
                title=landing_data["title"],
                slug=landing_data["slug"],
                status=LandingStatus.READY,
                version=1,
            )
            self.db.add(landing)
            await self.db.flush()

            for i, section_data in enumerate(landing_data["sections"]):
                self.db.add(LandingSection(
                    landing_page_id=landing.id,
                    section_type=section_data["section_type"],
                    position=i,
                    content=section_data["content"],
                ))

            await self._attach_control_variant(campaign_id, landing, angle, offer)

            wallet.balance -= settings.PLAN_LANDING_COST
            self.db.add(CreditTransaction(
                workspace_id=workspace_id,
                wallet_id=wallet.id,
                amount=-settings.PLAN_LANDING_COST,
                transaction_type=TransactionType.USAGE,
                description="Generate landing page",
                reference_type="landing_page",
                reference_id=campaign_id,
            ))
            campaign.status = CampaignStatus.LANDING_READY
            await self.db.flush()
            await self.db.refresh(landing)
            return landing
        except (InsufficientCreditsException, BadGatewayException):
            raise
        except Exception as exc:
            logger.error("Landing generation failed type=%s", type(exc).__name__)
            raise BadRequestException("Landing generation failed. Please try again.") from exc
