from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.campaign import Campaign
from app.models.tracking import LandingVariant
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.demo import DemoEventGenerator
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

router = APIRouter()


class GenerateDemoEventsRequest(BaseModel):
    variant_a_sessions: int = 500
    variant_b_sessions: int = 500
    variant_a_purchases: int = 18
    variant_b_purchases: int = 31
    days_back: int = 14


@router.post("/{campaign_id}/demo/events")
async def generate_demo_events(
    campaign_id: UUID,
    data: GenerateDemoEventsRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign")

    # Get variants
    variants_result = await db.execute(
        select(LandingVariant).where(LandingVariant.campaign_id == campaign_id).order_by(LandingVariant.variant_key)
    )
    variants = variants_result.scalars().all()

    if len(variants) < 2:
        raise BadRequestException("Campaign must have at least 2 variants to generate demo events")

    variant_a = variants[0]
    variant_b = variants[1]

    generator = DemoEventGenerator(db)
    result = await generator.generate_for_campaign(
        campaign_id=campaign_id,
        workspace_id=workspace.id,
        variant_a_id=variant_a.id,
        variant_b_id=variant_b.id,
        variant_a_sessions=data.variant_a_sessions,
        variant_b_sessions=data.variant_b_sessions,
        variant_a_purchases=data.variant_a_purchases,
        variant_b_purchases=data.variant_b_purchases,
        days_back=data.days_back,
    )

    return result


@router.delete("/{campaign_id}/demo/events")
async def clear_demo_events(
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

    generator = DemoEventGenerator(db)
    cleared = await generator.clear_campaign_events(campaign_id)

    return {"cleared": cleared}
