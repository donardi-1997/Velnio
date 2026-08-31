from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class CampaignCreate(BaseModel):
    product_id: Optional[UUID] = None
    name: str = Field(..., max_length=512)
    store_id: Optional[UUID] = None
    target_country: str = "US"
    target_language: str = "en"
    currency: str = "USD"
    selling_price: Optional[float] = None
    supplier_price: Optional[float] = None
    target_audience: Optional[str] = None
    payment_strategy: Optional[str] = None
    shipping_strategy: Optional[str] = None
    notes: Optional[str] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    store_id: Optional[UUID] = None
    target_country: Optional[str] = None
    target_language: Optional[str] = None
    currency: Optional[str] = None
    selling_price: Optional[float] = None
    supplier_price: Optional[float] = None
    target_audience: Optional[str] = None
    payment_strategy: Optional[str] = None
    shipping_strategy: Optional[str] = None
    notes: Optional[str] = None
    tracking_key: Optional[str] = None


class CampaignResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    product_id: Optional[UUID] = None
    store_id: Optional[UUID] = None
    name: str
    status: str
    target_country: str
    target_language: str
    currency: str
    selling_price: Optional[float] = None
    supplier_price: Optional[float] = None
    target_audience: Optional[str] = None
    payment_strategy: Optional[str] = None
    shipping_strategy: Optional[str] = None
    notes: Optional[str] = None
    external_product_id: Optional[str] = None
    external_page_id: Optional[str] = None
    external_page_handle: Optional[str] = None
    external_page_url: Optional[str] = None
    published_at: Optional[datetime] = None
    last_publish_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
