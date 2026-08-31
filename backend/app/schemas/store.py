from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class StoreResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    shop_domain: Optional[str] = None
    platform: str
    status: str
    country: str
    currency: str
    created_at: datetime

    class Config:
        from_attributes = True


class MockStoreConnect(BaseModel):
    name: str = "My Shopify Store"
    shop_domain: str = "my-store.myshopify.com"
    country: str = "US"
    currency: str = "USD"
