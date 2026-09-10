from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class GoogleDriveStatus(BaseModel):
    connected: bool
    google_email: Optional[str] = None
    google_name: Optional[str] = None
    connected_at: Optional[datetime] = None


class GoogleDriveFile(BaseModel):
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    thumbnail_url: Optional[str] = None
    created_time: Optional[str] = None
    modified_time: Optional[str] = None
    web_view_link: Optional[str] = None
    is_folder: bool = False


class GoogleDriveFolder(BaseModel):
    id: str
    name: str
    files: List[GoogleDriveFile] = Field(default_factory=list)
    folders: List[GoogleDriveFile] = Field(default_factory=list)


class GoogleDriveSearchResult(BaseModel):
    files: List[GoogleDriveFile]
    next_page_token: Optional[str] = None


class GoogleDriveImportImageRequest(BaseModel):
    file_id: str
    product_id: UUID
    purpose: str = "ORIGINAL"
    position: int = 0


class GoogleDriveImportDocumentRequest(BaseModel):
    file_id: str
    product_id: UUID
    campaign_id: Optional[UUID] = None


class GoogleDriveImportAssetRequest(BaseModel):
    file_id: str
    campaign_id: UUID
    purpose: str = "OTHER"


class GoogleDriveImportResponse(BaseModel):
    id: UUID
    file_name: Optional[str] = None
    file_type: str
    status: str
    storage_key: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime


class ProductSourceDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    external_file_id: str
    external_file_name: Optional[str] = None
    file_type: str
    file_size: Optional[int] = None
    status: str
    storage_key: Optional[str] = None
    content_text: Optional[str] = None
    extracted_text: Optional[str] = None
    character_count: Optional[int] = None
    page_count: Optional[int] = None
    extraction_error: Optional[str] = None
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime


class GoogleDriveConnectRequest(BaseModel):
    code: str
    state: str
