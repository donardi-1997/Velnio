from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.core.config import settings
from app.core.exceptions import BadRequestException, InsufficientCreditsException, NotFoundException
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.analysis import ProductAnalysis
from app.models.angle import SellingAngle
from app.models.campaign import Campaign
from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.offer import Offer
from app.models.product import Product
from app.models.workspace import Workspace
from app.schemas.offer import OfferResponse, OfferUpdate
from app.services.ai import get_ai_provider

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{campaign_id}/offer", response_model=OfferResponse)
async def get_campaign_offer(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundException("Campaign")
    offer_result = await db.execute(select(Offer).where(Offer.campaign_id == campaign_id))
    offer = offer_result.scalar_one_or_none()
    if not offer:
        raise NotFoundException("Offer")
    return offer


@router.post("/{campaign_id}/offer/generate", response_model=OfferResponse)
async def generate_campaign_offer(
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

    angle_result = await db.execute(
        select(SellingAngle).where(SellingAngle.campaign_id == campaign_id, SellingAngle.selected == True)
    )
    angle = angle_result.scalar_one_or_none()
    if not angle:
        raise BadRequestException("Please select a selling angle first")

    analysis_result = await db.execute(
        select(ProductAnalysis).where(ProductAnalysis.product_id == product.id)
    )
    analysis = analysis_result.scalar_one_or_none()

    wallet_result = await db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace.id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet or wallet.balance < settings.PLAN_OFFER_COST:
        raise InsufficientCreditsException()

    existing_result = await db.execute(select(Offer).where(Offer.campaign_id == campaign_id))
    existing_offer = existing_result.scalar_one_or_none()
    if existing_offer:
        await db.delete(existing_offer)
        await db.flush()

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
        db.add(offer)

        wallet.balance -= settings.PLAN_OFFER_COST
        db.add(
            CreditTransaction(
                workspace_id=workspace.id,
                wallet_id=wallet.id,
                amount=-settings.PLAN_OFFER_COST,
                transaction_type=TransactionType.USAGE,
                description="Generate offer",
                reference_type="offer",
                reference_id=campaign_id,
            )
        )
        await db.flush()
        await db.refresh(offer)
        return offer
    except InsufficientCreditsException:
        raise
    except Exception as exc:
        logger.error(f"Offer generation failed: {exc}")
        raise BadRequestException("Offer generation failed. Please try again.")


@router.patch("/offers/{offer_id}", response_model=OfferResponse)
async def update_offer(
    offer_id: UUID,
    data: OfferUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    offer_result = await db.execute(
        select(Offer).join(Campaign).where(
            Offer.id == offer_id,
            Campaign.workspace_id == workspace.id,
        )
    )
    offer = offer_result.scalar_one_or_none()
    if not offer:
        raise NotFoundException("Offer")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(offer, key, value)
    await db.flush()
    await db.refresh(offer)
    return offer
