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
from app.models.campaign import Campaign, CampaignStatus
from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.landing import LandingPage, LandingSection, LandingStatus
from app.models.offer import Offer
from app.models.product import Product
from app.models.workspace import Workspace
from app.schemas.landing import LandingPageResponse
from app.services.ai import get_ai_provider

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{campaign_id}/landing", response_model=LandingPageResponse)
async def get_campaign_landing(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundException("Campaign")
    landing_result = await db.execute(
        select(LandingPage).where(LandingPage.campaign_id == campaign_id)
    )
    landing = landing_result.scalar_one_or_none()
    if not landing:
        raise NotFoundException("Landing page")
    return landing


@router.post("/{campaign_id}/landing/generate", response_model=LandingPageResponse)
async def generate_campaign_landing(
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

    offer_result = await db.execute(select(Offer).where(Offer.campaign_id == campaign_id))
    offer = offer_result.scalar_one_or_none()

    wallet_result = await db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace.id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet or wallet.balance < settings.PLAN_LANDING_COST:
        raise InsufficientCreditsException()

    existing_result = await db.execute(select(LandingPage).where(LandingPage.campaign_id == campaign_id))
    existing_landing = existing_result.scalar_one_or_none()
    if existing_landing:
        sections_result = await db.execute(
            select(LandingSection).where(LandingSection.landing_page_id == existing_landing.id)
        )
        for section in sections_result.scalars().all():
            await db.delete(section)
        await db.delete(existing_landing)
        await db.flush()

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
        db.add(landing)
        await db.flush()

        for i, section_data in enumerate(landing_data["sections"]):
            db.add(
                LandingSection(
                    landing_page_id=landing.id,
                    section_type=section_data["section_type"],
                    position=i,
                    content=section_data["content"],
                )
            )

        wallet.balance -= settings.PLAN_LANDING_COST
        db.add(
            CreditTransaction(
                workspace_id=workspace.id,
                wallet_id=wallet.id,
                amount=-settings.PLAN_LANDING_COST,
                transaction_type=TransactionType.USAGE,
                description="Generate landing page",
                reference_type="landing_page",
                reference_id=campaign_id,
            )
        )

        campaign.status = CampaignStatus.LANDING_READY
        await db.flush()
        await db.refresh(landing)
        return landing
    except InsufficientCreditsException:
        raise
    except Exception as exc:
        logger.error(f"Landing generation failed: {exc}")
        raise BadRequestException("Landing generation failed. Please try again.")
