from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.campaigns.application.offers import CampaignOfferService
from app.schemas.offer import OfferResponse, OfferUpdate

router = APIRouter()


def get_offer_service(db: AsyncSession = Depends(get_db)) -> CampaignOfferService:
    return CampaignOfferService(db)


@router.get("/{campaign_id}/offer", response_model=OfferResponse)
async def get_campaign_offer(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignOfferService = Depends(get_offer_service),
):
    return await service.get(campaign_id, workspace.id)


@router.post("/{campaign_id}/offer/generate", response_model=OfferResponse)
async def generate_campaign_offer(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignOfferService = Depends(get_offer_service),
):
    return await service.generate(campaign_id, workspace.id)


@router.patch("/offers/{offer_id}", response_model=OfferResponse)
async def update_offer(
    offer_id: UUID,
    data: OfferUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    service: CampaignOfferService = Depends(get_offer_service),
):
    return await service.update(offer_id, data, workspace.id)
