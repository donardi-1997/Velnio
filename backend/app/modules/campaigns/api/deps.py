from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.campaigns.application import CampaignService
from app.modules.campaigns.infrastructure import CampaignRepository


def get_campaign_service(
    db: AsyncSession = Depends(get_db),
) -> CampaignService:
    return CampaignService(CampaignRepository(db))
