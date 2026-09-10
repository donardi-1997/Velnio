from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.analytics.application.dashboard import DashboardService
from app.schemas.dashboard import DashboardSummary

router = APIRouter()


def get_dashboard_service(db: AsyncSession = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    workspace: Workspace = Depends(get_current_workspace),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.summary(workspace.id)
