from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.campaigns.application.landings import CampaignLandingService
from app.schemas.landing import LandingPageResponse

router = APIRouter()


def get_landing_service(db: AsyncSession = Depends(get_db)) -> CampaignLandingService:
    return CampaignLandingService(db)


@router.get("/{campaign_id}/landing", response_model=LandingPageResponse)
async def get_campaign_landing(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignLandingService = Depends(get_landing_service),
):
    return await service.get(campaign_id, workspace.id)


@router.post("/{campaign_id}/landing/generate", response_model=LandingPageResponse)
async def generate_campaign_landing(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignLandingService = Depends(get_landing_service),
):
    return await service.generate(campaign_id, workspace.id)
