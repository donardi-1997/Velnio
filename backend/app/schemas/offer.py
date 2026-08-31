from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class OfferCreate(BaseModel):
    headline: str = ""
    offer_type: str = "STANDARD"
    primary_price: Optional[float] = None
    compare_at_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    bundle_quantity: Optional[int] = None
    free_shipping: bool = False
    cash_on_delivery: bool = False
    guarantee_days: Optional[int] = None
    urgency_text: Optional[str] = None
    scarcity_text: Optional[str] = None
    bonus_text: Optional[str] = None


class OfferUpdate(BaseModel):
    headline: Optional[str] = None
    offer_type: Optional[str] = None
    primary_price: Optional[float] = None
    compare_at_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    bundle_quantity: Optional[int] = None
    free_shipping: Optional[bool] = None
    cash_on_delivery: Optional[bool] = None
    guarantee_days: Optional[int] = None
    urgency_text: Optional[str] = None
    scarcity_text: Optional[str] = None
    bonus_text: Optional[str] = None


class OfferResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    headline: str
    offer_type: str
    primary_price: Optional[float] = None
    compare_at_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    bundle_quantity: Optional[int] = None
    free_shipping: bool
    cash_on_delivery: bool
    guarantee_days: Optional[int] = None
    urgency_text: Optional[str] = None
    scarcity_text: Optional[str] = None
    bonus_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
