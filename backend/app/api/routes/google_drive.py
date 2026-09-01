from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime, timezone, timedelta
import secrets

from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.user import User
from app.models.product import Product, ProductImage, ImageSourceType
from app.models.campaign import Campaign
from app.models.google_drive import GoogleDriveConnection, ProductSourceDocument, DocumentImportStatus
from app.schemas.google_drive import (
    GoogleDriveStatus, GoogleDriveFile, GoogleDriveFolder, GoogleDriveSearchResult,
    GoogleDriveConnectRequest, GoogleDriveImportImageRequest, GoogleDriveImportDocumentRequest,
    GoogleDriveImportAssetRequest, GoogleDriveImportResponse, ProductSourceDocumentResponse,
)
from app.api.deps import get_current_workspace, get_current_user
from app.core.exceptions import NotFoundException, BadRequestException
from app.core.encryption import encrypt_value, decrypt_value
from app.services.google_drive import get_google_drive_provider
from app.services.storage import get_storage_provider
from app.core.config import settings

router = APIRouter()

IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp", "image/tiff"}
DOCUMENT_MIMETYPES = {"application/pdf", "text/plain", "text/html", "text/csv"}
GOOGLE_DOCS_MIMETYPES = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
}
EXPORT_MIMETYPES = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
}
MAX_FILE_SIZE = settings.GOOGLE_DRIVE_MAX_FILE_MB * 1024 * 1024


def _is_image(mime_type: str) -> bool:
    return mime_type in IMAGE_MIMETYPES


def _is_document(mime_type: str) -> bool:
    return mime_type in DOCUMENT_MIMETYPES or mime_type in GOOGLE_DOCS_MIMETYPES


def _is_folder(mime_type: str) -> bool:
    return mime_type == "application/vnd.google-apps.folder"


def _format_file(file_data: dict) -> GoogleDriveFile:
    return GoogleDriveFile(
        id=file_data["id"],
        name=file_data["name"],
        mime_type=file_data["mimeType"],
        size=file_data.get("size"),
        thumbnail_url=file_data.get("thumbnailLink"),
        created_time=file_data.get("createdTime"),
        modified_time=file_data.get("modifiedTime"),
        web_view_link=file_data.get("webViewLink"),
        is_folder=_is_folder(file_data["mimeType"]),
    )


@router.get("/status", response_model=GoogleDriveStatus)
async def get_drive_status(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GoogleDriveConnection).where(
            GoogleDriveConnection.workspace_id == workspace.id,
            GoogleDriveConnection.is_active == True,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        return GoogleDriveStatus(connected=False)
    return GoogleDriveStatus(
        connected=True,
        google_email=conn.google_email,
        google_name=conn.google_name,
        connected_at=conn.created_at,
    )


@router.get("/connect")
async def connect_drive(
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
):
    provider = get_google_drive_provider()
    state = secrets.token_urlsafe(32)
    auth_url = await provider.get_auth_url(state)
    return {"auth_url": auth_url, "state": state}


@router.get("/callback")
async def handle_drive_callback(
    code: str = Query(...),
    state: str = Query(...),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = get_google_drive_provider()
    try:
        token_data = await provider.exchange_code(code)
    except Exception as e:
        raise BadRequestException(f"Failed to authenticate with Google Drive: {str(e)[:200]}")

    existing_result = await db.execute(
        select(GoogleDriveConnection).where(
            GoogleDriveConnection.workspace_id == workspace.id,
            GoogleDriveConnection.is_active == True,
        )
    )
    existing_conn = existing_result.scalar_one_or_none()
    if existing_conn:
        existing_conn.is_active = False

    conn = GoogleDriveConnection(
        workspace_id=workspace.id,
        user_id=user.id,
        access_token_encrypted=encrypt_value(token_data["access_token"]),
        refresh_token_encrypted=encrypt_value(token_data["refresh_token"]),
        token_expiry=datetime.utcnow().replace(second=0) + timedelta(seconds=token_data.get("expires_in", 3600)),
        scope=token_data.get("scope", settings.GOOGLE_DRIVE_SCOPES),
        is_active=True,
    )
    db.add(conn)
    await db.flush()

    return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings?drive=connected")


@router.post("/connect-mock")
async def connect_drive_mock(
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = get_google_drive_provider()
    token_data = await provider.exchange_code("mock_code")

    existing_result = await db.execute(
        select(GoogleDriveConnection).where(
            GoogleDriveConnection.workspace_id == workspace.id,
            GoogleDriveConnection.is_active == True,
        )
    )
    existing_conn = existing_result.scalar_one_or_none()
    if existing_conn:
        existing_conn.is_active = False

    conn = GoogleDriveConnection(
        workspace_id=workspace.id,
        user_id=user.id,
        access_token_encrypted=encrypt_value(token_data["access_token"]),
        refresh_token_encrypted=encrypt_value(token_data["refresh_token"]),
        token_expiry=datetime.utcnow().replace(second=0) + timedelta(seconds=token_data.get("expires_in", 3600)),
        scope=token_data.get("scope", settings.GOOGLE_DRIVE_SCOPES),
        google_email="demo@gmail.com",
        google_name="Demo User",
        is_active=True,
    )
    db.add(conn)
    await db.flush()

    return {"connected": True, "google_email": "demo@gmail.com", "google_name": "Demo User"}


@router.post("/disconnect")
async def disconnect_drive(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GoogleDriveConnection).where(
            GoogleDriveConnection.workspace_id == workspace.id,
            GoogleDriveConnection.is_active == True,
        )
    )
    conn = result.scalar_one_or_none()
    if conn:
        conn.is_active = False
        await db.flush()
    return {"disconnected": True}


async def _get_valid_token(conn: GoogleDriveConnection, provider) -> str:
    access_token = decrypt_value(conn.access_token_encrypted)
    if conn.token_expiry:
        expiry = conn.token_expiry
        if expiry.tzinfo is not None:
            now = datetime.now(timezone.utc)
        else:
            now = datetime.now()
        if expiry < now:
            try:
                refresh_token = decrypt_value(conn.refresh_token_encrypted)
                token_data = await provider.refresh_token(refresh_token)
                access_token = token_data["access_token"]
            except Exception:
                pass
    return access_token


@router.get("/browse/{folder_id}")
async def browse_folder(
    folder_id: str,
    page_size: int = Query(50, ge=1, le=100),
    page_token: str = Query(None),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GoogleDriveConnection).where(
            GoogleDriveConnection.workspace_id == workspace.id,
            GoogleDriveConnection.is_active == True,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise BadRequestException("Google Drive not connected")

    provider = get_google_drive_provider()
    access_token = await _get_valid_token(conn, provider)

    data = await provider.list_files(
        access_token=access_token,
        folder_id=folder_id,
        page_size=page_size,
        page_token=page_token,
    )

    files = [_format_file(f) for f in data.get("files", [])]
    folders = [f for f in files if f.is_folder]
    file_items = [f for f in files if not f.is_folder]

    return GoogleDriveFolder(
        id=folder_id,
        name="Root" if folder_id == "root" else folder_id,
        files=file_items,
        folders=folders,
    )


@router.get("/search")
async def search_files(
    q: str = Query(..., min_length=1),
    page_size: int = Query(20, ge=1, le=100),
    page_token: str = Query(None),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GoogleDriveConnection).where(
            GoogleDriveConnection.workspace_id == workspace.id,
            GoogleDriveConnection.is_active == True,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise BadRequestException("Google Drive not connected")

    provider = get_google_drive_provider()
    access_token = await _get_valid_token(conn, provider)

    search_query = f"name contains '{q}' and trashed=false"
    data = await provider.list_files(
        access_token=access_token,
        folder_id="root",
        page_size=page_size,
        page_token=page_token,
        query=search_query,
    )

    files = [_format_file(f) for f in data.get("files", [])]
    return GoogleDriveSearchResult(
        files=files,
        next_page_token=data.get("nextPageToken"),
    )


@router.post("/import-image", response_model=GoogleDriveImportResponse)
async def import_image_from_drive(
    data: GoogleDriveImportImageRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    product_result = await db.execute(
        select(Product).where(Product.id == data.product_id, Product.workspace_id == workspace.id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise NotFoundException("Product")

    conn_result = await db.execute(
        select(GoogleDriveConnection).where(
            GoogleDriveConnection.workspace_id == workspace.id,
            GoogleDriveConnection.is_active == True,
        )
    )
    conn = conn_result.scalar_one_or_none()
    if not conn:
        raise BadRequestException("Google Drive not connected")

    provider = get_google_drive_provider()
    access_token = await _get_valid_token(conn, provider)

    file_data = await provider.get_file(access_token, data.file_id)
    if not _is_image(file_data.get("mimeType", "")):
        raise BadRequestException("File is not an image")

    existing_result = await db.execute(
        select(ProductImage).where(
            ProductImage.product_id == product.id,
            ProductImage.external_source == "GOOGLE_DRIVE",
            ProductImage.external_file_id == data.file_id,
        )
    )
    existing_image = existing_result.scalar_one_or_none()
    if existing_image:
        return GoogleDriveImportResponse(
            id=existing_image.id,
            file_name=file_data.get("name"),
            file_type=file_data.get("mimeType"),
            status="IMPORTED",
            storage_key=existing_image.storage_key,
            image_url=existing_image.image_url,
            created_at=existing_image.created_at,
        )

    content = await provider.download_file(access_token, data.file_id)
    if len(content) > MAX_FILE_SIZE:
        raise BadRequestException(f"File exceeds {settings.GOOGLE_DRIVE_MAX_FILE_MB}MB limit")

    ext = file_data["name"].rsplit(".", 1)[-1] if "." in file_data["name"] else "jpg"
    storage_key = f"products/{product.id}/images/{data.file_id}.{ext}"
    storage = get_storage_provider()
    storage_key = await storage.save_bytes(content, file_data.get("mimeType", "image/jpeg"), f"products/{product.id}/images")
    image_url = storage.get_public_url(storage_key)

    image = ProductImage(
        product_id=product.id,
        image_url=image_url,
        image_type=data.purpose,
        position=data.position,
        generated_by_ai="false",
        source_type="SOURCE",
        purpose=data.purpose,
        storage_key=storage_key,
        external_source="GOOGLE_DRIVE",
        external_file_id=data.file_id,
        external_file_name=file_data.get("name"),
    )
    db.add(image)
    await db.flush()
    await db.refresh(image)

    return GoogleDriveImportResponse(
        id=image.id,
        file_name=file_data.get("name"),
        file_type=file_data.get("mimeType"),
        status="IMPORTED",
        storage_key=storage_key,
        image_url=image_url,
        created_at=image.created_at,
    )


@router.post("/import-document", response_model=ProductSourceDocumentResponse)
async def import_document_from_drive(
    data: GoogleDriveImportDocumentRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    product_result = await db.execute(
        select(Product).where(Product.id == data.product_id, Product.workspace_id == workspace.id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise NotFoundException("Product")

    conn_result = await db.execute(
        select(GoogleDriveConnection).where(
            GoogleDriveConnection.workspace_id == workspace.id,
            GoogleDriveConnection.is_active == True,
        )
    )
    conn = conn_result.scalar_one_or_none()
    if not conn:
        raise BadRequestException("Google Drive not connected")

    provider = get_google_drive_provider()
    access_token = await _get_valid_token(conn, provider)

    file_data = await provider.get_file(access_token, data.file_id)
    mime_type = file_data.get("mimeType", "")

    if _is_image(mime_type):
        raise BadRequestException("Use /import-image for image files")

    content_text = None
    storage_key = None
    file_size = int(file_data.get("size", 0) or 0)

    if mime_type in EXPORT_MIMETYPES:
        export_mime = EXPORT_MIMETYPES[mime_type]
        content = await provider.export_file(access_token, data.file_id, export_mime)
        content_text = content.decode("utf-8", errors="replace")
        file_size = len(content)
    elif _is_document(mime_type):
        if mime_type == "application/pdf":
            content = await provider.download_file(access_token, data.file_id)
            file_size = len(content)
            storage_key = f"products/{product.id}/documents/{data.file_id}.pdf"
            storage = get_storage_provider()
            storage_key = await storage.save_bytes(content, "application/pdf", f"products/{product.id}/documents")
        elif mime_type == "text/plain":
            content = await provider.download_file(access_token, data.file_id)
            content_text = content.decode("utf-8", errors="replace")
            file_size = len(content)
    else:
        raise BadRequestException(f"Unsupported file type: {mime_type}")

    doc = ProductSourceDocument(
        product_id=product.id,
        workspace_id=workspace.id,
        campaign_id=data.campaign_id,
        external_file_id=data.file_id,
        external_file_name=file_data.get("name"),
        file_type=mime_type,
        file_size=file_size,
        status=DocumentImportStatus.PROCESSING,
        storage_key=storage_key,
        content_text=content_text,
        imported_by_user_id=user.id,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Auto-extract text
    from app.services.knowledge.extraction import DocumentExtractionService
    from app.services.storage import get_storage_provider

    extraction_service = DocumentExtractionService()
    storage = get_storage_provider()
    result = await extraction_service.extract(doc, storage)

    # Update document with extraction results
    doc.extracted_text = result.text
    doc.character_count = result.character_count
    doc.page_count = result.page_count
    doc.extraction_error = result.error
    doc.processed_at = datetime.now(timezone.utc)

    if result.status == "NEEDS_OCR":
        doc.status = DocumentImportStatus.NEEDS_OCR
    elif result.status == "FAILED":
        doc.status = DocumentImportStatus.FAILED
    else:
        doc.status = DocumentImportStatus.READY

    await db.flush()
    await db.refresh(doc)

    return doc


@router.post("/import-asset", response_model=GoogleDriveImportResponse)
async def import_asset_from_drive(
    data: GoogleDriveImportAssetRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign_result = await db.execute(
        select(Campaign).where(Campaign.id == data.campaign_id, Campaign.workspace_id == workspace.id)
    )
    campaign = campaign_result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign")

    conn_result = await db.execute(
        select(GoogleDriveConnection).where(
            GoogleDriveConnection.workspace_id == workspace.id,
            GoogleDriveConnection.is_active == True,
        )
    )
    conn = conn_result.scalar_one_or_none()
    if not conn:
        raise BadRequestException("Google Drive not connected")

    provider = get_google_drive_provider()
    access_token = await _get_valid_token(conn, provider)

    file_data = await provider.get_file(access_token, data.file_id)
    mime_type = file_data.get("mimeType", "")

    if not _is_image(mime_type):
        raise BadRequestException("Campaign assets must be images")

    content = await provider.download_file(access_token, data.file_id)
    if len(content) > MAX_FILE_SIZE:
        raise BadRequestException(f"File exceeds {settings.GOOGLE_DRIVE_MAX_FILE_MB}MB limit")

    ext = file_data["name"].rsplit(".", 1)[-1] if "." in file_data["name"] else "jpg"
    storage_key = f"campaigns/{campaign.id}/assets/{data.file_id}.{ext}"
    storage = get_storage_provider()
    storage_key = await storage.save_bytes(content, file_data.get("mimeType", "image/jpeg"), f"campaigns/{campaign.id}/assets")
    image_url = storage.get_public_url(storage_key)

    product_result = await db.execute(select(Product).where(Product.id == campaign.product_id))
    product = product_result.scalar_one_or_none()
    product_id = product.id if product else None

    image = ProductImage(
        product_id=product_id,
        campaign_id=campaign.id,
        image_url=image_url,
        image_type=data.purpose,
        position=0,
        generated_by_ai="false",
        source_type="SOURCE",
        purpose=data.purpose,
        storage_key=storage_key,
        external_source="GOOGLE_DRIVE",
        external_file_id=data.file_id,
        external_file_name=file_data.get("name"),
    )
    db.add(image)
    await db.flush()
    await db.refresh(image)

    return GoogleDriveImportResponse(
        id=image.id,
        file_name=file_data.get("name"),
        file_type=mime_type,
        status="IMPORTED",
        storage_key=storage_key,
        image_url=image_url,
        created_at=image.created_at,
    )


@router.get("/documents/{product_id}", response_model=list[ProductSourceDocumentResponse])
async def list_product_documents(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    product_result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    if not product_result.scalar_one_or_none():
        raise NotFoundException("Product")

    result = await db.execute(
        select(ProductSourceDocument)
        .where(ProductSourceDocument.product_id == product_id, ProductSourceDocument.workspace_id == workspace.id)
        .order_by(ProductSourceDocument.created_at.desc())
    )
    return result.scalars().all()
