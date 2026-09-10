from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    shop_domain: Optional[str] = None
    platform: str
    status: str
    country: str
    currency: str
    granted_scopes: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    created_at: datetime


class MockStoreConnect(BaseModel):
    name: str = "My Shopify Store"
    shop_domain: str = "my-store.myshopify.com"
    country: str = "US"
    currency: str = "USD"


class ShopifyConnectRequest(BaseModel):
    shop_domain: str

    @field_validator("shop_domain")
    @classmethod
    def normalize_input(cls, value: str) -> str:
        value = value.strip().lower()
        if value.startswith("https://"):
            value = value.removeprefix("https://")
        if value.startswith("http://"):
            value = value.removeprefix("http://")
        return value.rstrip("/").rstrip(".")


class ShopifyConnectResponse(BaseModel):
    auth_url: str
