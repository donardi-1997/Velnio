from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.catalog.application.imports import ProductImportService
from app.schemas.product import ProductResponse

router = APIRouter()


class ImportPreviewRequest(BaseModel):
    url: str


class ImageInfo(BaseModel):
    url: str
    position: int = 0


class ImportPreviewResponse(BaseModel):
    source_type: str
    source_url: str
    source_domain: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "USD"
    images: List[ImageInfo] = []
    confidence: dict = {}
    metadata: dict = {}


class CreateFromImportRequest(BaseModel):
    name: str
    description: Optional[str] = None
    selling_price: Optional[float] = None
    supplier_price: Optional[float] = None
    currency: str = "USD"
    source_url: Optional[str] = None
    source_type: str = "OTHER"
    source_domain: Optional[str] = None
    source_metadata: Optional[dict] = None
    images: List[ImageInfo] = []
    target_country: str = "US"
    target_language: str = "en"
    store_id: Optional[UUID] = None


def get_import_service(db: AsyncSession = Depends(get_db)) -> ProductImportService:
    return ProductImportService(db)


@router.post("/import/preview", response_model=ImportPreviewResponse)
async def preview_import(
    data: ImportPreviewRequest,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductImportService = Depends(get_import_service),
):
    result = await service.preview(data.url)
    return ImportPreviewResponse(
        source_type=result.get("source_type", "OTHER"),
        source_url=result.get("source_url", data.url),
        source_domain=result.get("source_domain"),
        name=result.get("name"),
        description=result.get("description"),
        price=result.get("price"),
        currency=result.get("currency", "USD"),
        images=[
            ImageInfo(
                url=image if isinstance(image, str) else image.get("url", ""),
                position=index,
            )
            for index, image in enumerate(result.get("images", []))
        ],
        confidence=result.get("confidence", {}),
        metadata=result.get("metadata", {}),
    )


@router.post("/import/create", response_model=ProductResponse, status_code=201)
async def create_from_import(
    data: CreateFromImportRequest,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductImportService = Depends(get_import_service),
):
    return await service.create(data, workspace.id)


@router.post("/{product_id}/images/upload", response_model=ProductResponse)
async def upload_product_images(
    product_id: UUID,
    files: List[UploadFile] = File(...),
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductImportService = Depends(get_import_service),
):
    return await service.upload_images(product_id, files, workspace.id)
