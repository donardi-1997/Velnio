from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.schemas.billing import PlanResponse, SubscriptionResponse
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException
from typing import List

router = APIRouter()


@router.get("/plans", response_model=List[PlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plan).where(Plan.active == True))
    return result.scalars().all()


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Subscription).where(Subscription.workspace_id == workspace.id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise NotFoundException("Subscription")
    return sub
