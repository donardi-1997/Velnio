from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_workspace
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.modules.campaigns.application.meta_ads_adsets import MetaAdsAdSetPublishingService
from app.modules.campaigns.application.meta_ads_publishing import MetaAdsCampaignPublishingService


router = APIRouter()


class MetaCampaignPublishRequest(BaseModel):
    ad_account_id: str = Field(pattern=r"^act_[0-9]+$", max_length=64)


class MetaDeliveryConfigRequest(BaseModel):
    pixel_id: str = Field(pattern=r"^[0-9]+$", max_length=128)
    page_id: str = Field(pattern=r"^[0-9]+$", max_length=128)
    instagram_account_id: str | None = Field(default=None, pattern=r"^[0-9]+$", max_length=128)


class MetaAdSetPublishRequest(BaseModel):
    daily_budget_minor: int = Field(gt=0)
    target_country: str | None = Field(default=None, pattern=r"^[A-Za-z]{2}$", max_length=2)


class MetaCampaignPublicationResponse(BaseModel):
    id: str
    campaign_id: str
    ad_account_id: str
    remote_campaign_id: str
    remote_campaign_name: str
    objective: str
    remote_status: str
    pixel_id: str | None = None
    page_id: str | None = None
    instagram_account_id: str | None = None
    delivery_configured_at: datetime | None = None
    created_at: datetime
    reused: bool = False


class MetaAdSetPublicationResponse(BaseModel):
    id: str
    campaign_publication_id: str
    remote_ad_set_id: str
    remote_ad_set_name: str
    remote_status: str
    target_country: str
    daily_budget_minor: int
    currency: str
    optimization_goal: str
    billing_event: str
    bid_strategy: str
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


@router.patch(
    "/{campaign_id}/meta-ads/publications/{publication_id}/delivery-config",
    response_model=MetaCampaignPublicationResponse,
)
async def configure_meta_campaign_delivery(
    campaign_id: UUID,
    publication_id: UUID,
    data: MetaDeliveryConfigRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MetaAdsCampaignPublishingService(db).configure_delivery(
        campaign_id,
        publication_id,
        workspace.id,
        user.id,
        data.pixel_id,
        data.page_id,
        data.instagram_account_id,
    )


@router.get(
    "/{campaign_id}/meta-ads/publications/{publication_id}/ad-set",
    response_model=MetaAdSetPublicationResponse | None,
)
async def get_meta_ad_set(
    campaign_id: UUID,
    publication_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await MetaAdsAdSetPublishingService(db).get_ad_set(
        campaign_id,
        publication_id,
        workspace.id,
    )


@router.post(
    "/{campaign_id}/meta-ads/publications/{publication_id}/ad-set",
    response_model=MetaAdSetPublicationResponse,
)
async def publish_meta_ad_set_paused(
    campaign_id: UUID,
    publication_id: UUID,
    data: MetaAdSetPublishRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MetaAdsAdSetPublishingService(db).publish_paused_ad_set(
        campaign_id,
        publication_id,
        workspace.id,
        user.id,
        data.daily_budget_minor,
        data.target_country,
    )
