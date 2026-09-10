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
from app.models.campaign import Campaign
from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.offer import Offer
from app.models.product import Product
from app.modules.campaigns.infrastructure import CampaignRepository
from app.schemas.offer import OfferUpdate
from app.services.ai import get_ai_provider

logger = get_logger(__name__)


class CampaignOfferService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.campaigns = CampaignRepository(db)

    async def get(self, campaign_id: UUID, workspace_id: UUID) -> Offer:
        if await self.campaigns.get_for_workspace(campaign_id, workspace_id) is None:
            raise NotFoundException("Campaign")
        result = await self.db.execute(select(Offer).where(Offer.campaign_id == campaign_id))
        offer = result.scalar_one_or_none()
        if offer is None:
            raise NotFoundException("Offer")
        return offer

    async def generate(self, campaign_id: UUID, workspace_id: UUID) -> Offer:
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

        wallet_result = await self.db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace_id))
        wallet = wallet_result.scalar_one_or_none()
        if wallet is None or wallet.balance < settings.PLAN_OFFER_COST:
            raise InsufficientCreditsException()

        existing_result = await self.db.execute(select(Offer).where(Offer.campaign_id == campaign_id))
        existing_offer = existing_result.scalar_one_or_none()
        if existing_offer:
            await self.db.delete(existing_offer)
            await self.db.flush()

        try:
            offer_data = await get_ai_provider().generate_offer(product, campaign, analysis, angle)
            offer = Offer(
                campaign_id=campaign_id,
                headline=offer_data.get("headline", ""),
                offer_type=offer_data.get("offer_type", "STANDARD"),
                primary_price=offer_data.get("primary_price"),
                compare_at_price=offer_data.get("compare_at_price"),
                discount_percentage=offer_data.get("discount_percentage"),
                bundle_quantity=offer_data.get("bundle_quantity"),
                free_shipping=offer_data.get("free_shipping", False),
                cash_on_delivery=offer_data.get("cash_on_delivery", False),
                guarantee_days=offer_data.get("guarantee_days"),
                urgency_text=offer_data.get("urgency_text"),
                scarcity_text=offer_data.get("scarcity_text"),
                bonus_text=offer_data.get("bonus_text"),
            )
            self.db.add(offer)
            wallet.balance -= settings.PLAN_OFFER_COST
            self.db.add(CreditTransaction(
                workspace_id=workspace_id,
                wallet_id=wallet.id,
                amount=-settings.PLAN_OFFER_COST,
                transaction_type=TransactionType.USAGE,
                description="Generate offer",
                reference_type="offer",
                reference_id=campaign_id,
            ))
            await self.db.flush()
            await self.db.refresh(offer)
            return offer
        except (InsufficientCreditsException, BadGatewayException):
            raise
        except Exception as exc:
            logger.error("Offer generation failed type=%s", type(exc).__name__)
            raise BadRequestException("Offer generation failed. Please try again.") from exc

    async def update(self, offer_id: UUID, data: OfferUpdate, workspace_id: UUID) -> Offer:
        result = await self.db.execute(
            select(Offer).join(Campaign).where(Offer.id == offer_id, Campaign.workspace_id == workspace_id)
        )
        offer = result.scalar_one_or_none()
        if offer is None:
            raise NotFoundException("Offer")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(offer, key, value)
        await self.db.flush()
        await self.db.refresh(offer)
        return offer
