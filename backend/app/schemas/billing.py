from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    monthly_price: float
    included_credits: int
    max_stores: int
    max_products_per_month: int
    active: bool


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    plan_id: UUID
    status: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    provider: str
    plan: Optional[PlanResponse] = None
