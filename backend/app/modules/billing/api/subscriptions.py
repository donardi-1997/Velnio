from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.billing.application.subscriptions import SubscriptionService
from app.modules.billing.infrastructure.repository import BillingRepository
from app.schemas.billing import PlanResponse, SubscriptionResponse

router = APIRouter()


def get_subscription_service(db: AsyncSession = Depends(get_db)) -> SubscriptionService:
    return SubscriptionService(BillingRepository(db))


@router.get("/plans", response_model=List[PlanResponse])
async def list_plans(
    service: SubscriptionService = Depends(get_subscription_service),
):
    return await service.list_plans()


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    workspace: Workspace = Depends(get_current_workspace),
    service: SubscriptionService = Depends(get_subscription_service),
):
    return await service.get_subscription(workspace.id)
