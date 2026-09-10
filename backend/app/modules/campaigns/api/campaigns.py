from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.models.product import Product
from app.models.store import Store
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


@router.get("/by-product/{product_id}", response_model=List[CampaignResponse])
async def list_campaigns_for_product(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignService = Depends(get_campaign_service),
    db: AsyncSession = Depends(get_db),
):
    product_result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    if not product_result.scalar_one_or_none():
        raise NotFoundException("Product")
    return await service.repository.list_for_product(product_id, workspace.id)


@router.post("/by-product/{product_id}", response_model=CampaignResponse, status_code=201)
async def create_campaign_for_product(
    product_id: UUID,
    data: CampaignCreate,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignService = Depends(get_campaign_service),
    db: AsyncSession = Depends(get_db),
):
    product_result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    if not product_result.scalar_one_or_none():
        raise NotFoundException("Product")

    if data.store_id:
        store_result = await db.execute(
            select(Store).where(Store.id == data.store_id, Store.workspace_id == workspace.id)
        )
        if not store_result.scalar_one_or_none():
            raise NotFoundException("Store")

    payload = data.model_copy(update={"product_id": product_id})
    return await service.create(payload, workspace.id)


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
