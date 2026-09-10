from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.campaigns.application.angles import CampaignAngleService
from app.schemas.angle import SellingAngleResponse

router = APIRouter()


def get_angle_service(db: AsyncSession = Depends(get_db)) -> CampaignAngleService:
    return CampaignAngleService(db)


@router.get("/{campaign_id}/angles", response_model=List[SellingAngleResponse])
async def list_campaign_angles(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignAngleService = Depends(get_angle_service),
):
    return await service.list(campaign_id, workspace.id)


@router.post("/{campaign_id}/angles/generate", response_model=List[SellingAngleResponse])
async def generate_campaign_angles(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignAngleService = Depends(get_angle_service),
):
    return await service.generate(campaign_id, workspace.id)


@router.post("/{campaign_id}/angles/{angle_id}/select", response_model=SellingAngleResponse)
async def select_campaign_angle(
    campaign_id: UUID,
    angle_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignAngleService = Depends(get_angle_service),
):
    return await service.select(campaign_id, angle_id, workspace.id)
