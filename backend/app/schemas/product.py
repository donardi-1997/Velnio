from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=512)
    source_url: Optional[str] = None
    source_type: str = "MANUAL"
    supplier_price: Optional[float] = None
    selling_price: Optional[float] = None
    currency: str = "USD"
    description: Optional[str] = None
    target_country: str = "US"
    target_language: str = "en"
    store_id: Optional[UUID] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    source_url: Optional[str] = None
    supplier_price: Optional[float] = None
    selling_price: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    target_country: Optional[str] = None
    target_language: Optional[str] = None
    store_id: Optional[UUID] = None


class ProductImageResponse(BaseModel):
    id: UUID
    image_url: str
    image_type: str
    position: int
    generated_by_ai: str
    source_type: str = "SOURCE"
    purpose: str = "ORIGINAL"
    external_source: Optional[str] = None
    external_file_id: Optional[str] = None
    external_file_name: Optional[str] = None
    selected: bool = False

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    store_id: Optional[UUID] = None
    name: str
    source_type: str
    source_url: Optional[str] = None
    supplier_price: Optional[float] = None
    selling_price: Optional[float] = None
    currency: str
    description: Optional[str] = None
    target_country: str
    target_language: str
    status: str
    published_product_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    images: List[ProductImageResponse] = []

    class Config:
        from_attributes = True
