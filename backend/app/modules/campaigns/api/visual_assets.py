from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.campaigns.application.visual_assets import CampaignVisualAssetService

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
    return await CampaignVisualAssetService(db).generate_visual_direction(campaign_id, workspace.id)


@router.get("/{campaign_id}/visual-direction", response_model=VisualDirectionResponse)
async def get_visual_direction(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await CampaignVisualAssetService(db).get_visual_direction(campaign_id, workspace.id)


@router.patch("/visual-directions/{vd_id}", response_model=VisualDirectionResponse)
async def update_visual_direction(
    vd_id: UUID,
    data: VisualDirectionUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await CampaignVisualAssetService(db).update_visual_direction(vd_id, workspace.id, data)


@router.post("/{campaign_id}/assets/generate")
async def generate_launch_pack(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await CampaignVisualAssetService(db).generate_launch_pack(campaign_id, workspace.id)


@router.post("/{campaign_id}/assets/{image_id}/select")
async def select_asset(
    campaign_id: UUID,
    image_id: UUID,
    purpose: str = "HERO",
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await CampaignVisualAssetService(db).select_asset(campaign_id, image_id, purpose, workspace.id)
