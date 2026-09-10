from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.campaigns.application.product_scope import ProductScopedCampaignService
from app.schemas.angle import SellingAngleResponse
from app.schemas.landing import LandingPageResponse, LandingSectionResponse, LandingSectionUpdate, LandingUpdate

router = APIRouter()


def get_product_scoped_campaign_service(
    db: AsyncSession = Depends(get_db),
) -> ProductScopedCampaignService:
    return ProductScopedCampaignService(db)


@router.get("/{product_id}/angles", response_model=List[SellingAngleResponse])
async def list_angles(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductScopedCampaignService = Depends(get_product_scoped_campaign_service),
):
    return await service.list_angles(product_id, workspace.id)


@router.post("/{product_id}/angles/generate", response_model=List[SellingAngleResponse])
async def generate_angles(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductScopedCampaignService = Depends(get_product_scoped_campaign_service),
):
    return await service.generate_angles(product_id, workspace.id)


@router.post("/{product_id}/angles/{angle_id}/select", response_model=SellingAngleResponse)
async def select_angle(
    product_id: UUID,
    angle_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductScopedCampaignService = Depends(get_product_scoped_campaign_service),
):
    return await service.select_angle(product_id, angle_id, workspace.id)


@router.get("/{product_id}/landing", response_model=LandingPageResponse)
async def get_landing(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductScopedCampaignService = Depends(get_product_scoped_campaign_service),
):
    return await service.get_landing(product_id, workspace.id)


@router.post("/{product_id}/landing/generate", response_model=LandingPageResponse)
async def generate_landing(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductScopedCampaignService = Depends(get_product_scoped_campaign_service),
):
    return await service.generate_landing(product_id, workspace.id)


@router.get("/landing-sections/{section_id}", response_model=LandingSectionResponse)
async def get_landing_section(
    section_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductScopedCampaignService = Depends(get_product_scoped_campaign_service),
):
    return await service.get_section(section_id, workspace.id)


@router.patch("/landing-sections/{section_id}", response_model=LandingSectionResponse)
async def update_landing_section(
    section_id: UUID,
    data: LandingSectionUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductScopedCampaignService = Depends(get_product_scoped_campaign_service),
):
    return await service.update_section(section_id, data.content, workspace.id)


@router.patch("/landings/{landing_id}", response_model=LandingPageResponse)
async def update_landing(
    landing_id: UUID,
    data: LandingUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductScopedCampaignService = Depends(get_product_scoped_campaign_service),
):
    return await service.update_landing(landing_id, data, workspace.id)
