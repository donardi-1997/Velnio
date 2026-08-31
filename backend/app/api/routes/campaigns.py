from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.product import Product
from app.models.store import Store, StoreStatus
from app.models.campaign import Campaign, CampaignStatus
from app.models.angle import SellingAngle
from app.models.analysis import ProductAnalysis
from app.models.landing import LandingPage, LandingSection, LandingStatus
from app.models.offer import Offer
from app.models.credit import CreditWallet, CreditTransaction, TransactionType
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse
from app.schemas.angle import SellingAngleResponse
from app.schemas.landing import LandingPageResponse, LandingSectionUpdate
from app.schemas.offer import OfferResponse, OfferUpdate
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException, InsufficientCreditsException, BadRequestException
from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai import get_ai_provider
from app.services.shopify import get_shopify_provider
from typing import List
from uuid import UUID
from datetime import datetime, timezone

logger = get_logger(__name__)
router = APIRouter()


# Campaign CRUD

@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.workspace_id == workspace.id).order_by(Campaign.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    data: CampaignCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    campaign = Campaign(
        workspace_id=workspace.id,
        product_id=data.product_id,
        name=data.name,
        target_country=data.target_country,
        target_language=data.target_language,
        currency=data.currency,
        selling_price=data.selling_price,
        supplier_price=data.supplier_price,
        target_audience=data.target_audience,
        payment_strategy=data.payment_strategy,
        shipping_strategy=data.shipping_strategy,
        notes=data.notes,
        store_id=data.store_id,
    )
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
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
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(campaign, key, value)
    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(
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
    await db.delete(campaign)
    await db.flush()
    return None


# Product-scoped campaign endpoints

@router.get("/by-product/{product_id}", response_model=List[CampaignResponse])
async def list_campaigns_for_product(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    product_result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    if not product_result.scalar_one_or_none():
        raise NotFoundException("Product")
    result = await db.execute(
        select(Campaign).where(Campaign.product_id == product_id, Campaign.workspace_id == workspace.id).order_by(Campaign.created_at.desc())
    )
    return result.scalars().all()


@router.post("/by-product/{product_id}", response_model=CampaignResponse, status_code=201)
async def create_campaign_for_product(
    product_id: UUID,
    data: CampaignCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    product_result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise NotFoundException("Product")

    if data.store_id:
        store_result = await db.execute(
            select(Store).where(Store.id == data.store_id, Store.workspace_id == workspace.id)
        )
        if not store_result.scalar_one_or_none():
            raise NotFoundException("Store")

    campaign = Campaign(
        workspace_id=workspace.id,
        product_id=product_id,
        store_id=data.store_id,
        name=data.name,
        target_country=data.target_country,
        target_language=data.target_language,
        currency=data.currency,
        selling_price=data.selling_price,
        supplier_price=data.supplier_price,
        target_audience=data.target_audience,
        payment_strategy=data.payment_strategy,
        shipping_strategy=data.shipping_strategy,
        notes=data.notes,
    )
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return campaign


# Campaign Angles

@router.get("/{campaign_id}/angles", response_model=List[SellingAngleResponse])
async def list_campaign_angles(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundException("Campaign")
    angles_result = await db.execute(
        select(SellingAngle).where(SellingAngle.campaign_id == campaign_id).order_by(SellingAngle.position)
    )
    return angles_result.scalars().all()


@router.post("/{campaign_id}/angles/generate", response_model=List[SellingAngleResponse])
async def generate_campaign_angles(
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

    wallet_result = await db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace.id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet or wallet.balance < settings.PLAN_ANGLES_COST:
        raise InsufficientCreditsException()

    try:
        ai = get_ai_provider()
        angles_data = await ai.generate_selling_angles_for_campaign(product, campaign)

        existing_result = await db.execute(
            select(SellingAngle).where(SellingAngle.campaign_id == campaign_id)
        )
        for old_angle in existing_result.scalars().all():
            await db.delete(old_angle)
        await db.flush()

        created_angles = []
        for i, angle_data in enumerate(angles_data):
            angle = SellingAngle(
                campaign_id=campaign_id,
                product_id=product.id,
                name=angle_data["name"],
                target_audience=angle_data["target_audience"],
                pain_point=angle_data["pain_point"],
                main_promise=angle_data["main_promise"],
                hook=angle_data["hook"],
                description=angle_data["description"],
                score=angle_data["score"],
                position=i + 1,
                selected=False,
            )
            db.add(angle)
            created_angles.append(angle)

        wallet.balance -= settings.PLAN_ANGLES_COST
        tx = CreditTransaction(
            workspace_id=workspace.id,
            wallet_id=wallet.id,
            amount=-settings.PLAN_ANGLES_COST,
            transaction_type=TransactionType.USAGE,
            description="Generate selling angles",
            reference_type="selling_angles",
            reference_id=campaign_id,
        )
        db.add(tx)

        if campaign.status == CampaignStatus.DRAFT:
            campaign.status = CampaignStatus.ANGLE_READY

        await db.flush()
        for angle in created_angles:
            await db.refresh(angle)
        return created_angles

    except InsufficientCreditsException:
        raise
    except Exception as e:
        logger.error(f"Angle generation failed: {e}")
        raise BadRequestException("Angle generation failed. Please try again.")


@router.post("/{campaign_id}/angles/{angle_id}/select", response_model=SellingAngleResponse)
async def select_campaign_angle(
    campaign_id: UUID,
    angle_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundException("Campaign")

    angle_result = await db.execute(
        select(SellingAngle).where(SellingAngle.id == angle_id, SellingAngle.campaign_id == campaign_id)
    )
    angle = angle_result.scalar_one_or_none()
    if not angle:
        raise NotFoundException("Angle")

    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(SellingAngle).where(SellingAngle.campaign_id == campaign_id).values(selected=False)
    )
    angle.selected = True

    campaign_result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = campaign_result.scalar_one()
    if campaign.status in [CampaignStatus.DRAFT, CampaignStatus.ANALYZING]:
        campaign.status = CampaignStatus.ANGLE_READY

    await db.flush()
    await db.refresh(angle)
    return angle


# Campaign Offer

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
        ai = get_ai_provider()
        offer_data = await ai.generate_offer(product, campaign, analysis, angle)

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
        tx = CreditTransaction(
            workspace_id=workspace.id,
            wallet_id=wallet.id,
            amount=-settings.PLAN_OFFER_COST,
            transaction_type=TransactionType.USAGE,
            description="Generate offer",
            reference_type="offer",
            reference_id=campaign_id,
        )
        db.add(tx)

        await db.flush()
        await db.refresh(offer)
        return offer

    except InsufficientCreditsException:
        raise
    except Exception as e:
        logger.error(f"Offer generation failed: {e}")
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
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(offer, key, value)
    await db.flush()
    await db.refresh(offer)
    return offer


# Campaign Landing

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
        for s in sections_result.scalars().all():
            await db.delete(s)
        await db.delete(existing_landing)
        await db.flush()

    try:
        ai = get_ai_provider()
        landing_data = await ai.generate_landing_for_campaign(product, campaign, angle, analysis, offer)

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
            reference_id=campaign_id,
        )
        db.add(tx)

        campaign.status = CampaignStatus.LANDING_READY
        await db.flush()
        await db.refresh(landing)
        return landing

    except InsufficientCreditsException:
        raise
    except Exception as e:
        logger.error(f"Landing generation failed: {e}")
        raise BadRequestException("Landing generation failed. Please try again.")


# Campaign Publish

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

    if campaign.store_id:
        store_result = await db.execute(select(Store).where(Store.id == campaign.store_id))
        store = store_result.scalar_one_or_none()
    else:
        store = None

    angle_result = await db.execute(
        select(SellingAngle).where(SellingAngle.campaign_id == campaign_id, SellingAngle.selected == True)
    )
    angle = angle_result.scalar_one_or_none()

    landing_result = await db.execute(
        select(LandingPage).where(LandingPage.campaign_id == campaign_id)
    )
    landing = landing_result.scalar_one_or_none()

    offer_result = await db.execute(select(Offer).where(Offer.campaign_id == campaign_id))
    offer = offer_result.scalar_one_or_none()

    try:
        provider = get_shopify_provider()
        publish_result = await provider.publish_campaign(campaign, product, store, angle, landing, offer)

        from sqlalchemy import update as sa_update
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

    except Exception as e:
        logger.error(f"Publish failed: {e}")
        from sqlalchemy import update as sa_update
        await db.execute(
            sa_update(Campaign).where(Campaign.id == campaign_id).values(
                status=CampaignStatus.FAILED,
                last_publish_error=str(e)[:500],
            )
        )
        await db.flush()
        raise BadRequestException(f"Publish failed: {str(e)[:200]}")
