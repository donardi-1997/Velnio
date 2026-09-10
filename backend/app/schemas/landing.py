from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime


class LandingSectionUpdate(BaseModel):
    content: dict


class LandingUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None


class LandingSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    landing_page_id: UUID
    section_type: str
    position: int
    content: Any
    created_at: datetime
    updated_at: datetime


class LandingPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: Optional[UUID] = None
    campaign_id: Optional[UUID] = None
    selling_angle_id: Optional[UUID] = None
    title: str
    slug: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    sections: List[LandingSectionResponse] = Field(default_factory=list)
