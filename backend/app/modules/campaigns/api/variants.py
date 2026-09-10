from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.campaigns.application.variants import CampaignVariantService

router = APIRouter()


class VariantCreateRequest(BaseModel):
    name: str
    clone_from_variant_id: Optional[UUID] = None


class VariantUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    traffic_weight: Optional[float] = None
    selling_angle_id: Optional[UUID] = None
    offer_id: Optional[UUID] = None


class TrafficWeightsRequest(BaseModel):
    weights: Dict[str, float]


@router.get("/{campaign_id}/variants")
async def list_variants(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await CampaignVariantService(db).list(campaign_id, workspace.id)


@router.post("/{campaign_id}/variants", status_code=201)
async def create_variant(
    campaign_id: UUID,
    data: VariantCreateRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await CampaignVariantService(db).create(
        campaign_id, workspace.id, data.name, data.clone_from_variant_id
    )


@router.patch("/{campaign_id}/variants/traffic")
async def update_traffic_weights(
    campaign_id: UUID,
    data: TrafficWeightsRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await CampaignVariantService(db).update_traffic(campaign_id, workspace.id, data.weights)


@router.patch("/{campaign_id}/variants/{variant_id}")
async def update_variant(
    campaign_id: UUID,
    variant_id: UUID,
    data: VariantUpdateRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await CampaignVariantService(db).update(campaign_id, variant_id, workspace.id, data)


@router.delete("/{campaign_id}/variants/{variant_id}", status_code=204)
async def delete_variant(
    campaign_id: UUID,
    variant_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    await CampaignVariantService(db).delete(campaign_id, variant_id, workspace.id)
    return None
