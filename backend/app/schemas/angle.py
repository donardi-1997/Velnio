from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class SellingAngleResponse(BaseModel):
    id: UUID
    product_id: Optional[UUID] = None
    campaign_id: Optional[UUID] = None
    name: str
    target_audience: str
    pain_point: str
    main_promise: str
    hook: str
    description: str
    score: float
    position: int
    selected: bool
    created_at: datetime

    class Config:
        from_attributes = True
