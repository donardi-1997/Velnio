from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.campaigns.application.publishing import CampaignPublishingService

router = APIRouter()


@router.get("/{campaign_id}/publish-readiness")
async def publish_readiness(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await CampaignPublishingService(db).readiness(campaign_id, workspace.id)


@router.post("/{campaign_id}/publish")
async def publish_campaign(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await CampaignPublishingService(db).publish(campaign_id, workspace.id)
