from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.campaigns.application.briefs import CampaignBriefService

router = APIRouter()


@router.post("/{campaign_id}/generate-brief")
async def generate_campaign_brief(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CampaignBriefService(db).generate(campaign_id, workspace.id, user.id)
