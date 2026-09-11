from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_workspace
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.modules.campaigns.application.meta_ads_ads import MetaAdsAdPublishingService
from app.modules.campaigns.application.meta_ads_adsets import MetaAdsAdSetPublishingService
from app.modules.campaigns.application.meta_ads_creatives import MetaAdsCreativePublishingService
from app.modules.campaigns.application.meta_ads_launch_readiness import MetaAdsLaunchReadinessService
from app.modules.campaigns.application.meta_ads_publishing import MetaAdsCampaignPublishingService


router = APIRouter()
MAX_SAFE_DAILY_BUDGET_MINOR = 9_007_199_254_740_991


class MetaCampaignPublishRequest(BaseModel):
    ad_account_id: str = Field(pattern=r"^act_[0-9]+$", max_length=64)


class MetaDeliveryConfigRequest(BaseModel):
    pixel_id: str = Field(pattern=r"^[0-9]+$", max_length=128)
    page_id: str = Field(pattern=r"^[0-9]+$", max_length=128)
    instagram_account_id: str | None = Field(default=None, pattern=r"^[0-9]+$", max_length=128)


class MetaAdSetPublishRequest(BaseModel):
    daily_budget_minor: int = Field(gt=0, le=MAX_SAFE_DAILY_BUDGET_MINOR)
    target_country: str | None = Field(default=None, pattern=r"^[A-Za-z]{2}$", max_length=2)


class MetaCreativePublishRequest(BaseModel):
    product_image_id: UUID
    primary_text: str = Field(min_length=1, max_length=5000)
    headline: str | None = Field(default=None, max_length=255)
    call_to_action: Literal["SHOP_NOW", "LEARN_MORE", "GET_OFFER"] = "SHOP_NOW"


class MetaAdPublishRequest(BaseModel):
    creative_publication_id: UUID


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


class MetaCreativePublicationResponse(BaseModel):
    id: str
    campaign_publication_id: str
    ad_set_publication_id: str
    product_image_id: str | None
    remote_creative_id: str
    remote_creative_name: str
    destination_url: str
    image_url: str
    primary_text: str
    headline: str | None
    call_to_action: str
    page_id: str
    instagram_account_id: str | None
    created_at: datetime
    reused: bool = False


class MetaAdPublicationResponse(BaseModel):
    id: str
    campaign_publication_id: str
    ad_set_publication_id: str
    creative_publication_id: str
    remote_ad_id: str
    remote_ad_name: str
    remote_status: str
    created_at: datetime
    reused: bool = False


class MetaAdRemoteStateResponse(BaseModel):
    ad_publication_id: str
    remote_ad_id: str
    account_id: str
    campaign_id: str
    adset_id: str
    creative_id: str
    configured_status: str
    effective_status: str | None = None


class MetaLaunchCheckResponse(BaseModel):
    key: str
    status: Literal["PASS", "FAIL"]
    message: str


class MetaLaunchPlanResponse(BaseModel):
    ad_account_id: str
    remote_campaign_id: str
    remote_ad_set_id: str
    remote_ad_id: str
    remote_creative_id: str
    destination_url: str
    pixel_id: str | None
    page_id: str | None
    instagram_account_id: str | None
    daily_budget_minor: int
    currency: str
    target_country: str
    current_configured_statuses: dict[str, str | None]
    proposed_statuses: dict[str, str]


class MetaLaunchReadinessResponse(BaseModel):
    ready: bool
    side_effects_performed: bool
    checks: list[MetaLaunchCheckResponse]
    launch_plan: MetaLaunchPlanResponse


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


@router.get(
    "/{campaign_id}/meta-ads/publications/{publication_id}/creatives",
    response_model=list[MetaCreativePublicationResponse],
)
async def list_meta_creatives(
    campaign_id: UUID,
    publication_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await MetaAdsCreativePublishingService(db).list_creatives(
        campaign_id,
        publication_id,
        workspace.id,
    )


@router.post(
    "/{campaign_id}/meta-ads/publications/{publication_id}/creatives",
    response_model=MetaCreativePublicationResponse,
)
async def publish_meta_creative(
    campaign_id: UUID,
    publication_id: UUID,
    data: MetaCreativePublishRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MetaAdsCreativePublishingService(db).publish_standalone_creative(
        campaign_id,
        publication_id,
        workspace.id,
        user.id,
        data.product_image_id,
        data.primary_text,
        data.headline,
        data.call_to_action,
    )


@router.get(
    "/{campaign_id}/meta-ads/publications/{publication_id}/ads",
    response_model=list[MetaAdPublicationResponse],
)
async def list_meta_ads(
    campaign_id: UUID,
    publication_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await MetaAdsAdPublishingService(db).list_ads(
        campaign_id,
        publication_id,
        workspace.id,
    )


@router.get(
    "/{campaign_id}/meta-ads/publications/{publication_id}/ads/{ad_publication_id}/remote-state",
    response_model=MetaAdRemoteStateResponse,
)
async def get_meta_ad_remote_state(
    campaign_id: UUID,
    publication_id: UUID,
    ad_publication_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await MetaAdsAdPublishingService(db).get_remote_state(
        campaign_id,
        publication_id,
        ad_publication_id,
        workspace.id,
    )


@router.get(
    "/{campaign_id}/meta-ads/publications/{publication_id}/ads/{ad_publication_id}/launch-readiness",
    response_model=MetaLaunchReadinessResponse,
)
async def get_meta_launch_readiness(
    campaign_id: UUID,
    publication_id: UUID,
    ad_publication_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MetaAdsLaunchReadinessService(db).get_readiness(
        campaign_id,
        publication_id,
        ad_publication_id,
        workspace.id,
        user.id,
    )


@router.post(
    "/{campaign_id}/meta-ads/publications/{publication_id}/ads",
    response_model=MetaAdPublicationResponse,
)
async def publish_meta_ad_paused(
    campaign_id: UUID,
    publication_id: UUID,
    data: MetaAdPublishRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MetaAdsAdPublishingService(db).publish_paused_ad(
        campaign_id,
        publication_id,
        workspace.id,
        user.id,
        data.creative_publication_id,
    )
