from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_workspace
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.modules.campaigns.application.meta_ads_publishing import MetaAdsCampaignPublishingService


router = APIRouter()


class MetaCampaignPublishRequest(BaseModel):
    ad_account_id: str = Field(pattern=r"^act_[0-9]+$", max_length=64)


class MetaCampaignPublicationResponse(BaseModel):
    id: str
    campaign_id: str
    ad_account_id: str
    remote_campaign_id: str
    remote_campaign_name: str
    objective: str
    remote_status: str
    created_at: datetime
    reused: bool = False


@router.get("/{campaign_id}/meta-ads/publications", response_model=list[MetaCampaignPublicationResponse])
async def list_meta_campaign_publications(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await MetaAdsCampaignPublishingService(db).list_publications(campaign_id, workspace.id)


@router.post("/{campaign_id}/meta-ads/publish", response_model=MetaCampaignPublicationResponse)
async def publish_meta_campaign_paused(
    campaign_id: UUID,
    data: MetaCampaignPublishRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MetaAdsCampaignPublishingService(db).publish_paused_campaign(
        campaign_id,
        workspace.id,
        user.id,
        data.ad_account_id,
    )
