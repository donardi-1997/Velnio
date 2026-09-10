from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.core.config import settings
from app.core.exceptions import BadRequestException, InsufficientCreditsException, NotFoundException
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.angle import SellingAngle
from app.models.campaign import Campaign, CampaignStatus
from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.product import Product
from app.models.workspace import Workspace
from app.schemas.angle import SellingAngleResponse
from app.services.ai import get_ai_provider
from app.services.knowledge.context_builder import KnowledgeContextBuilder

logger = get_logger(__name__)
router = APIRouter()


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
        knowledge_context = await KnowledgeContextBuilder().build(
            db=db,
            product_id=product.id,
            campaign_id=campaign.id,
            workspace_id=workspace.id,
        )
        angles_data = await get_ai_provider().generate_selling_angles_for_campaign(
            product, campaign, knowledge_context
        )

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
        db.add(
            CreditTransaction(
                workspace_id=workspace.id,
                wallet_id=wallet.id,
                amount=-settings.PLAN_ANGLES_COST,
                transaction_type=TransactionType.USAGE,
                description="Generate selling angles",
                reference_type="selling_angles",
                reference_id=campaign_id,
            )
        )

        if campaign.status == CampaignStatus.DRAFT:
            campaign.status = CampaignStatus.ANGLE_READY

        await db.flush()
        for angle in created_angles:
            await db.refresh(angle)
        return created_angles
    except InsufficientCreditsException:
        raise
    except Exception as exc:
        logger.error(f"Angle generation failed: {exc}")
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
