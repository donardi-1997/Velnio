from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.product import Product
from app.models.campaign import Campaign
from app.models.angle import SellingAngle
from app.models.analysis import ProductAnalysis
from app.models.landing import LandingPage, LandingSection, LandingStatus
from app.models.offer import Offer
from app.models.credit import CreditWallet, CreditTransaction, TransactionType
from app.schemas.landing import LandingPageResponse, LandingSectionResponse, LandingUpdate, LandingSectionUpdate
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException, InsufficientCreditsException, BadRequestException
from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai import get_ai_provider
from typing import List
from uuid import UUID

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{product_id}/landing", response_model=LandingPageResponse)
async def get_landing(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundException("Product")
    campaign_result = await db.execute(
        select(Campaign).where(Campaign.product_id == product_id, Campaign.workspace_id == workspace.id).limit(1)
    )
    campaign = campaign_result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("No campaign found for this product")
    landing_result = await db.execute(
        select(LandingPage).where(LandingPage.campaign_id == campaign.id)
    )
    landing = landing_result.scalar_one_or_none()
    if not landing:
        raise NotFoundException("Landing page")
    return landing


@router.post("/{product_id}/landing/generate", response_model=LandingPageResponse)
async def generate_landing(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundException("Product")

    campaign_result = await db.execute(
        select(Campaign).where(Campaign.product_id == product_id, Campaign.workspace_id == workspace.id).limit(1)
    )
    campaign = campaign_result.scalar_one_or_none()
    if not campaign:
        raise BadRequestException("Create a campaign first")

    angle_result = await db.execute(
        select(SellingAngle).where(SellingAngle.campaign_id == campaign.id, SellingAngle.selected == True)
    )
    angle = angle_result.scalar_one_or_none()
    if not angle:
        raise BadRequestException("Please select a selling angle first")

    analysis_result = await db.execute(
        select(ProductAnalysis).where(ProductAnalysis.product_id == product_id)
    )
    analysis = analysis_result.scalar_one_or_none()

    offer_result = await db.execute(select(Offer).where(Offer.campaign_id == campaign.id))
    offer = offer_result.scalar_one_or_none()

    wallet_result = await db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace.id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet or wallet.balance < settings.PLAN_LANDING_COST:
        raise InsufficientCreditsException()

    existing_result = await db.execute(select(LandingPage).where(LandingPage.campaign_id == campaign.id))
    existing_landing = existing_result.scalar_one_or_none()
    if existing_landing:
        sections_result = await db.execute(
            select(LandingSection).where(LandingSection.landing_page_id == existing_landing.id)
        )
        for s in sections_result.scalars().all():
            await db.delete(s)
        await db.delete(existing_landing)
        await db.flush()

    try:
        ai = get_ai_provider()
        product_obj = (await db.execute(select(Product).where(Product.id == product_id))).scalar_one()
        landing_data = await ai.generate_landing_for_campaign(product_obj, campaign, angle, analysis, offer)

        landing = LandingPage(
            campaign_id=campaign.id,
            product_id=product_id,
            selling_angle_id=angle.id,
            title=landing_data["title"],
            slug=landing_data["slug"],
            status=LandingStatus.READY,
            version=1,
        )
        db.add(landing)
        await db.flush()

        for i, section_data in enumerate(landing_data["sections"]):
            section = LandingSection(
                landing_page_id=landing.id,
                section_type=section_data["section_type"],
                position=i,
                content=section_data["content"],
            )
            db.add(section)

        wallet.balance -= settings.PLAN_LANDING_COST
        tx = CreditTransaction(
            workspace_id=workspace.id,
            wallet_id=wallet.id,
            amount=-settings.PLAN_LANDING_COST,
            transaction_type=TransactionType.USAGE,
            description="Generate landing page",
            reference_type="landing_page",
            reference_id=campaign.id,
        )
        db.add(tx)

        await db.flush()
        await db.refresh(landing)
        return landing

    except InsufficientCreditsException:
        raise
    except Exception as e:
        logger.error(f"Landing generation failed: {e}")
        raise BadRequestException("Landing generation failed. Please try again.")


@router.get("/landing-sections/{section_id}", response_model=LandingSectionResponse)
async def get_landing_section(
    section_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    section_result = await db.execute(
        select(LandingSection).join(LandingPage).join(Campaign).where(
            LandingSection.id == section_id,
            Campaign.workspace_id == workspace.id,
        )
    )
    section = section_result.scalar_one_or_none()
    if not section:
        raise NotFoundException("Landing section")
    return section


@router.patch("/landing-sections/{section_id}", response_model=LandingSectionResponse)
async def update_landing_section(
    section_id: UUID,
    data: LandingSectionUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    section_result = await db.execute(
        select(LandingSection).join(LandingPage).join(Campaign).where(
            LandingSection.id == section_id,
            Campaign.workspace_id == workspace.id,
        )
    )
    section = section_result.scalar_one_or_none()
    if not section:
        raise NotFoundException("Landing section")
    section.content = data.content
    await db.flush()
    await db.refresh(section)
    return section


@router.patch("/landings/{landing_id}", response_model=LandingPageResponse)
async def update_landing(
    landing_id: UUID,
    data: LandingUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    landing_result = await db.execute(
        select(LandingPage).join(Campaign).where(
            LandingPage.id == landing_id,
            Campaign.workspace_id == workspace.id,
        )
    )
    landing = landing_result.scalar_one_or_none()
    if not landing:
        raise NotFoundException("Landing page")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(landing, key, value)
    await db.flush()
    await db.refresh(landing)
    return landing
