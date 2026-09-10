from __future__ import annotations

import secrets
from typing import Sequence
from uuid import UUID

from app.core.exceptions import NotFoundException
from app.modules.campaigns.domain import Campaign
from app.modules.campaigns.infrastructure import CampaignRepository
from app.schemas.campaign import CampaignCreate, CampaignUpdate


class CampaignService:
    """Application service for campaign lifecycle operations."""

    def __init__(self, repository: CampaignRepository) -> None:
        self.repository = repository

    async def list(self, workspace_id: UUID) -> Sequence[Campaign]:
        return await self.repository.list_for_workspace(workspace_id)

    async def get(self, campaign_id: UUID, workspace_id: UUID) -> Campaign:
        campaign = await self.repository.get_for_workspace(campaign_id, workspace_id)
        if campaign is None:
            raise NotFoundException("Campaign")
        return campaign

    async def create(self, data: CampaignCreate, workspace_id: UUID) -> Campaign:
        campaign = Campaign(
            workspace_id=workspace_id,
            product_id=data.product_id,
            name=data.name,
            target_country=data.target_country,
            target_language=data.target_language,
            currency=data.currency,
            selling_price=data.selling_price,
            supplier_price=data.supplier_price,
            target_audience=data.target_audience,
            payment_strategy=data.payment_strategy,
            shipping_strategy=data.shipping_strategy,
            notes=data.notes,
            store_id=data.store_id,
            tracking_key=secrets.token_urlsafe(32),
        )
        return await self.repository.add(campaign)

    async def update(
        self,
        campaign_id: UUID,
        data: CampaignUpdate,
        workspace_id: UUID,
    ) -> Campaign:
        campaign = await self.get(campaign_id, workspace_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(campaign, key, value)
        return await self.repository.flush_and_refresh(campaign)

    async def delete(self, campaign_id: UUID, workspace_id: UUID) -> None:
        campaign = await self.get(campaign_id, workspace_id)
        await self.repository.delete(campaign)
