from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    cancel_at_period_end: bool = False
    trial_end: Optional[datetime] = None
    plan: Optional[PlanResponse] = None


class CheckoutSessionRequest(BaseModel):
    plan_code: str = Field(min_length=2, max_length=50)


class BillingSessionResponse(BaseModel):
    url: str
    session_id: Optional[str] = None


class BillingWebhookResponse(BaseModel):
    received: bool = True
    duplicate: bool = False


class EntitlementsResponse(BaseModel):
    plan_code: str
    plan_name: str
    subscription_status: str
    max_stores: int
    stores_used: int
    max_products_per_month: int
    products_used_this_month: int
    included_credits: int
