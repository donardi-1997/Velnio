from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class KnowledgeSourceCreate(BaseModel):
    product_id: Optional[UUID] = None
    campaign_id: Optional[UUID] = None
    source_type: str
    content_type: str
    title: str
    content_text: Optional[str] = None
    url: Optional[str] = None
    source_document_id: Optional[UUID] = None
    is_primary: bool = False


class KnowledgeSourceUpdate(BaseModel):
    title: Optional[str] = None
    content_text: Optional[str] = None
    url: Optional[str] = None
    is_primary: Optional[bool] = None
    status: Optional[str] = None


class KnowledgeSourceResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    product_id: Optional[UUID] = None
    campaign_id: Optional[UUID] = None
    source_type: str
    content_type: str
    title: str
    content_text: Optional[str] = None
    url: Optional[str] = None
    source_document_id: Optional[UUID] = None
    content_hash: Optional[str] = None
    imported_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    is_primary: bool
    status: str
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
