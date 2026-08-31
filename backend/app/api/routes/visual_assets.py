from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.product import Product, ProductImage, ImageSourceType, ImagePurpose
from app.models.campaign import Campaign
from app.models.angle import SellingAngle
from app.models.offer import Offer
from app.models.visual_direction import CampaignVisualDirection
from app.models.credit import CreditWallet, CreditTransaction, TransactionType
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException, InsufficientCreditsException, BadRequestException
from app.core.config import settings
from app.core.logging import get_logger
from app.services.images import get_image_provider
from app.services.images.prompts import VisualDirection
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

logger = get_logger(__name__)
router = APIRouter()


class VisualDirectionResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    visual_style: str
    tone: str
    color_notes: Optional[str] = None
    background_style: Optional[str] = None
    photography_style: Optional[str] = None
    audience_context: Optional[str] = None
    additional_instructions: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VisualDirectionUpdate(BaseModel):
    visual_style: Optional[str] = None
    tone: Optional[str] = None
    color_notes: Optional[str] = None
    background_style: Optional[str] = None
    photography_style: Optional[str] = None
    audience_context: Optional[str] = None
    additional_instructions: Optional[str] = None


@router.post("/{campaign_id}/visual-direction/generate", response_model=VisualDirectionResponse)
async def generate_visual_direction(
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
    if not wallet or wallet.balance < settings.PLAN_VISUAL_DIRECTION_COST:
        raise InsufficientCreditsException()

    existing_result = await db.execute(select(CampaignVisualDirection).where(CampaignVisualDirection.campaign_id == campaign_id))
    existing = existing_result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.flush()

    try:
        from app.services.images.prompts import generate_visual_direction_prompt
        vd_data = generate_visual_direction_prompt(product, campaign)

        vd = CampaignVisualDirection(
            campaign_id=campaign_id,
            visual_style=vd_data["visual_style"],
            tone=vd_data["tone"],
            color_notes=vd_data.get("color_notes"),
            background_style=vd_data.get("background_style"),
            photography_style=vd_data.get("photography_style"),
            audience_context=vd_data.get("audience_context"),
            additional_instructions=vd_data.get("additional_instructions"),
        )
        db.add(vd)

        wallet.balance -= settings.PLAN_VISUAL_DIRECTION_COST
        tx = CreditTransaction(
            workspace_id=workspace.id,
            wallet_id=wallet.id,
            amount=-settings.PLAN_VISUAL_DIRECTION_COST,
            transaction_type=TransactionType.USAGE,
            description="Generate visual direction",
            reference_type="visual_direction",
            reference_id=campaign_id,
        )
        db.add(tx)

        await db.flush()
        await db.refresh(vd)
        return vd

    except InsufficientCreditsException:
        raise
    except Exception as e:
        logger.error(f"Visual direction generation failed: {e}")
        raise BadRequestException("Visual direction generation failed.")


@router.get("/{campaign_id}/visual-direction", response_model=VisualDirectionResponse)
async def get_visual_direction(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundException("Campaign")

    vd_result = await db.execute(select(CampaignVisualDirection).where(CampaignVisualDirection.campaign_id == campaign_id))
    vd = vd_result.scalar_one_or_none()
    if not vd:
        raise NotFoundException("Visual direction not found")
    return vd


@router.patch("/visual-directions/{vd_id}", response_model=VisualDirectionResponse)
async def update_visual_direction(
    vd_id: UUID,
    data: VisualDirectionUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CampaignVisualDirection).join(Campaign).where(
            CampaignVisualDirection.id == vd_id,
            Campaign.workspace_id == workspace.id,
        )
    )
    vd = result.scalar_one_or_none()
    if not vd:
        raise NotFoundException("Visual direction")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(vd, key, value)
    await db.flush()
    await db.refresh(vd)
    return vd


@router.post("/{campaign_id}/assets/generate")
async def generate_launch_pack(
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

    offer_result = await db.execute(select(Offer).where(Offer.campaign_id == campaign_id))
    offer = offer_result.scalar_one_or_none()

    vd_result = await db.execute(select(CampaignVisualDirection).where(CampaignVisualDirection.campaign_id == campaign_id))
    vd = vd_result.scalar_one_or_none()

    visual_direction = None
    if vd:
        visual_direction = VisualDirection(
            visual_style=vd.visual_style,
            tone=vd.tone,
            color_notes=vd.color_notes,
            background_style=vd.background_style or "",
            photography_style=vd.photography_style or "",
            audience_context=vd.audience_context or "",
            additional_instructions=vd.additional_instructions or "",
        )

    wallet_result = await db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace.id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet or wallet.balance < settings.PLAN_LAUNCH_PACK_COST:
        raise InsufficientCreditsException()

    try:
        image_provider = get_image_provider()
        from app.services.storage import get_storage_provider
        storage = get_storage_provider()

        purposes = [
            (ImagePurpose.HERO, 1),
            (ImagePurpose.LIFESTYLE, 2),
            (ImagePurpose.PROBLEM, 1),
            (ImagePurpose.SOLUTION, 1),
            (ImagePurpose.BENEFIT, 2),
            (ImagePurpose.COMPARISON, 1),
        ]

        created_images = []
        for purpose, count in purposes:
            for _ in range(count):
                try:
                    result = await image_provider.generate_campaign_asset(
                        product, campaign, angle, offer, visual_direction, purpose.value
                    )
                    img = ProductImage(
                        product_id=product.id,
                        campaign_id=campaign_id,
                        image_url=result.get("image_url", ""),
                        source_type=ImageSourceType.AI_GENERATED,
                        purpose=purpose,
                        prompt=result.get("prompt"),
                        generation_provider=result.get("provider", settings.IMAGE_PROVIDER),
                        generation_model=result.get("model"),
                        width=result.get("width"),
                        height=result.get("height"),
                        position=len(created_images),
                    )
                    db.add(img)
                    created_images.append(img)
                except Exception as e:
                    logger.error(f"Failed to generate {purpose.value} image: {e}")

        wallet.balance -= settings.PLAN_LAUNCH_PACK_COST
        tx = CreditTransaction(
            workspace_id=workspace.id,
            wallet_id=wallet.id,
            amount=-settings.PLAN_LAUNCH_PACK_COST,
            transaction_type=TransactionType.USAGE,
            description="Generate Launch Pack",
            reference_type="campaign_asset",
            reference_id=campaign_id,
        )
        db.add(tx)

        await db.flush()
        for img in created_images:
            await db.refresh(img)

        return {
            "status": "generated",
            "count": len(created_images),
            "images": [{"id": str(img.id), "purpose": img.purpose, "url": img.image_url} for img in created_images],
        }

    except InsufficientCreditsException:
        raise
    except Exception as e:
        logger.error(f"Launch pack generation failed: {e}")
        raise BadRequestException("Launch pack generation failed.")


@router.post("/{campaign_id}/assets/{image_id}/select")
async def select_asset(
    campaign_id: UUID,
    image_id: UUID,
    purpose: str = "HERO",
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundException("Campaign")

    img_result = await db.execute(
        select(ProductImage).where(ProductImage.id == image_id, ProductImage.campaign_id == campaign_id)
    )
    img = img_result.scalar_one_or_none()
    if not img:
        raise NotFoundException("Image")

    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(ProductImage).where(
            ProductImage.campaign_id == campaign_id,
            ProductImage.purpose == purpose,
        ).values(selected=False)
    )
    img.selected = True
    img.purpose = purpose

    await db.flush()
    return {"status": "selected", "image_id": str(img.id), "purpose": purpose}
