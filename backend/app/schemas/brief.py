from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class CampaignBriefResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    workspace_id: UUID
    product_summary: Optional[str] = None
    target_audience: Optional[str] = None
    key_benefits: Optional[str] = None
    tone_of_voice: Optional[str] = None
    pricing_strategy: Optional[str] = None
    positioning: Optional[str] = None
    generated_by_user_id: UUID
    generated_at: Optional[datetime] = None
    credit_cost: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
