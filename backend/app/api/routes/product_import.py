from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.product import Product, ProductImage, ProductStatus, SourceType, ImageSourceType, ImagePurpose
from app.models.credit import CreditWallet, CreditTransaction, TransactionType
from app.schemas.product import ProductCreate, ProductResponse
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException, InsufficientCreditsException, BadRequestException
from app.core.config import settings
from app.core.logging import get_logger
from app.services.import_engine import import_product_from_url
from app.services.storage import get_storage_provider
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

logger = get_logger(__name__)
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


@router.post("/import/preview", response_model=ImportPreviewResponse)
async def preview_import(
    data: ImportPreviewRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await import_product_from_url(data.url)
    return ImportPreviewResponse(
        source_type=result.get("source_type", "OTHER"),
        source_url=result.get("source_url", data.url),
        source_domain=result.get("source_domain"),
        name=result.get("name"),
        description=result.get("description"),
        price=result.get("price"),
        currency=result.get("currency", "USD"),
        images=[ImageInfo(url=img if isinstance(img, str) else img.get("url", ""), position=i) for i, img in enumerate(result.get("images", []))],
        confidence=result.get("confidence", {}),
        metadata=result.get("metadata", {}),
    )


@router.post("/import/create", response_model=ProductResponse, status_code=201)
async def create_from_import(
    data: CreateFromImportRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    product = Product(
        workspace_id=workspace.id,
        store_id=data.store_id,
        name=data.name,
        description=data.description,
        selling_price=data.selling_price,
        supplier_price=data.supplier_price,
        currency=data.currency,
        source_type=SourceType(data.source_type),
        source_url=data.source_url,
        source_domain=data.source_domain,
        source_metadata=data.source_metadata,
        target_country=data.target_country,
        target_language=data.target_language,
        status=ProductStatus.DRAFT,
    )
    db.add(product)
    await db.flush()

    for i, img in enumerate(data.images):
        product_img = ProductImage(
            product_id=product.id,
            image_url=img.url,
            source_type=ImageSourceType.SOURCE,
            purpose=ImagePurpose.ORIGINAL,
            position=img.position,
        )
        db.add(product_img)

    await db.flush()
    await db.refresh(product)
    return product


@router.post("/{product_id}/images/upload", response_model=ProductResponse)
async def upload_product_images(
    product_id: UUID,
    files: List[UploadFile] = File(...),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundException("Product")

    storage = get_storage_provider()
    max_size = settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024
    allowed_types = {"image/jpeg", "image/png", "image/webp"}

    existing_count = len(product.images) if product.images else 0

    for i, file in enumerate(files):
        if file.content_type not in allowed_types:
            raise BadRequestException(f"Invalid file type: {file.content_type}. Allowed: JPEG, PNG, WEBP")

        content = await file.read()
        if len(content) > max_size:
            raise BadRequestException(f"File too large: {file.filename}. Max size: {settings.MAX_IMAGE_UPLOAD_MB}MB")

        key = await storage.save_bytes(content, file.content_type, f"products/{product_id}")
        url = storage.get_public_url(key)

        img = ProductImage(
            product_id=product.id,
            image_url=url,
            storage_key=key,
            source_type=ImageSourceType.UPLOADED,
            purpose=ImagePurpose.ORIGINAL,
            position=existing_count + i,
        )
        db.add(img)

    await db.flush()
    await db.refresh(product)
    return product
