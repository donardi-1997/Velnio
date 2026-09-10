from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_workspace
from app.models.workspace import Workspace
from app.modules.campaigns.api.deps import get_campaign_service
from app.modules.campaigns.application import CampaignService
from app.schemas.campaign import CampaignCreate, CampaignResponse, CampaignUpdate

router = APIRouter()


@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignService = Depends(get_campaign_service),
):
    return await service.list(workspace.id)


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    data: CampaignCreate,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignService = Depends(get_campaign_service),
):
    return await service.create(data, workspace.id)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignService = Depends(get_campaign_service),
):
    return await service.get(campaign_id, workspace.id)


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignService = Depends(get_campaign_service),
):
    return await service.update(campaign_id, data, workspace.id)


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignService = Depends(get_campaign_service),
):
    await service.delete(campaign_id, workspace.id)
    return None
