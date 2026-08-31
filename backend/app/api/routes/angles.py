from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sa_update
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.product import Product, ProductStatus
from app.models.campaign import Campaign, CampaignStatus
from app.models.angle import SellingAngle
from app.models.credit import CreditWallet, CreditTransaction, TransactionType
from app.schemas.angle import SellingAngleResponse
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException, InsufficientCreditsException, BadRequestException
from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai import get_ai_provider
from typing import List
from uuid import UUID

logger = get_logger(__name__)
router = APIRouter()


async def _get_default_campaign(db: AsyncSession, product_id: UUID, workspace_id: UUID) -> Campaign:
    result = await db.execute(
        select(Campaign).where(Campaign.product_id == product_id, Campaign.workspace_id == workspace_id).limit(1)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        product_result = await db.execute(select(Product).where(Product.id == product_id))
        product = product_result.scalar_one_or_none()
        if not product:
            raise NotFoundException("Product")
        campaign = Campaign(
            workspace_id=workspace_id,
            product_id=product_id,
            name=f"Default Campaign - {product.target_country}",
            target_country=product.target_country,
            target_language=product.target_language,
            currency=product.currency,
            selling_price=product.selling_price,
            supplier_price=product.supplier_price,
            status=CampaignStatus.DRAFT,
        )
        db.add(campaign)
        await db.flush()
    return campaign


@router.get("/{product_id}/angles", response_model=List[SellingAngleResponse])
async def list_angles(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundException("Product")
    campaign = await _get_default_campaign(db, product_id, workspace.id)
    angles_result = await db.execute(
        select(SellingAngle).where(SellingAngle.campaign_id == campaign.id).order_by(SellingAngle.position)
    )
    return angles_result.scalars().all()


@router.post("/{product_id}/angles/generate", response_model=List[SellingAngleResponse])
async def generate_angles(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundException("Product")

    campaign = await _get_default_campaign(db, product_id, workspace.id)

    wallet_result = await db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace.id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet or wallet.balance < settings.PLAN_ANGLES_COST:
        raise InsufficientCreditsException()

    try:
        ai = get_ai_provider()
        angles_data = await ai.generate_selling_angles_for_campaign(product, campaign)

        existing_result = await db.execute(
            select(SellingAngle).where(SellingAngle.campaign_id == campaign.id)
        )
        for old_angle in existing_result.scalars().all():
            await db.delete(old_angle)
        await db.flush()

        created_angles = []
        for i, angle_data in enumerate(angles_data):
            angle = SellingAngle(
                campaign_id=campaign.id,
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
            reference_id=campaign.id,
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


@router.post("/{product_id}/angles/{angle_id}/select", response_model=SellingAngleResponse)
async def select_angle(
    product_id: UUID,
    angle_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundException("Product")

    campaign = await _get_default_campaign(db, product_id, workspace.id)

    angle_result = await db.execute(
        select(SellingAngle).where(SellingAngle.id == angle_id, SellingAngle.campaign_id == campaign.id)
    )
    angle = angle_result.scalar_one_or_none()
    if not angle:
        raise NotFoundException("Angle")

    await db.execute(
        sa_update(SellingAngle).where(SellingAngle.campaign_id == campaign.id).values(selected=False)
    )
    angle.selected = True
    if campaign.status in [CampaignStatus.DRAFT, CampaignStatus.ANALYZING]:
        campaign.status = CampaignStatus.ANGLE_READY
    await db.flush()
    await db.refresh(angle)
    return angle
