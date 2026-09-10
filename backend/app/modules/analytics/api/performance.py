from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.analytics.application.performance import PerformanceService

router = APIRouter()


def get_performance_service(db: AsyncSession = Depends(get_db)) -> PerformanceService:
    return PerformanceService(db)


@router.get("/{campaign_id}/performance")
async def get_performance(
    campaign_id: UUID,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    workspace: Workspace = Depends(get_current_workspace),
    service: PerformanceService = Depends(get_performance_service),
):
    return await service.get_performance(campaign_id, workspace.id, from_date, to_date)


@router.get("/{campaign_id}/performance/timeline")
async def get_performance_timeline(
    campaign_id: UUID,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    workspace: Workspace = Depends(get_current_workspace),
    service: PerformanceService = Depends(get_performance_service),
):
    return await service.get_timeline(campaign_id, workspace.id, from_date, to_date)


@router.get("/{campaign_id}/variants/performance")
async def get_variant_performance(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: PerformanceService = Depends(get_performance_service),
):
    return await service.get_variant_performance(campaign_id, workspace.id)


@router.get("/{campaign_id}/angles/performance")
async def get_angle_performance(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: PerformanceService = Depends(get_performance_service),
):
    return await service.get_angle_performance(campaign_id, workspace.id)


@router.post("/{campaign_id}/performance/analyze")
async def analyze_performance(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: PerformanceService = Depends(get_performance_service),
):
    return await service.analyze(campaign_id, workspace.id)
