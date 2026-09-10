from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_workspace
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.modules.integrations.application.google_drive_browser import GoogleDriveBrowserService
from app.modules.integrations.application.google_drive_connection import GoogleDriveConnectionService
from app.modules.integrations.application.google_drive_imports import GoogleDriveImportService
from app.schemas.google_drive import (
    GoogleDriveFolder,
    GoogleDriveImportAssetRequest,
    GoogleDriveImportDocumentRequest,
    GoogleDriveImportImageRequest,
    GoogleDriveImportResponse,
    GoogleDriveSearchResult,
    GoogleDriveStatus,
    ProductSourceDocumentResponse,
)

router = APIRouter()


def _connection(db: AsyncSession) -> GoogleDriveConnectionService:
    return GoogleDriveConnectionService(db)


@router.get("/status", response_model=GoogleDriveStatus)
async def get_drive_status(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await _connection(db).status(workspace.id)


@router.get("/connect")
async def connect_drive(
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _connection(db).auth_url()


@router.get("/callback")
async def handle_drive_callback(
    code: str = Query(...),
    state: str = Query(...),
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _connection(db).connect_from_code(workspace.id, user.id, code)
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings?drive=connected")


@router.post("/connect-mock")
async def connect_drive_mock(
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _connection(db).connect_mock(workspace.id, user.id)


@router.post("/disconnect")
async def disconnect_drive(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await _connection(db).disconnect(workspace.id)


@router.get("/browse/{folder_id}", response_model=GoogleDriveFolder)
async def browse_folder(
    folder_id: str,
    page_size: int = Query(50, ge=1, le=100),
    page_token: str | None = Query(None),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    connection = _connection(db)
    return await GoogleDriveBrowserService(connection).browse(
        workspace.id, folder_id, page_size, page_token
    )


@router.get("/search", response_model=GoogleDriveSearchResult)
async def search_files(
    q: str = Query(..., min_length=1),
    page_size: int = Query(20, ge=1, le=100),
    page_token: str | None = Query(None),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    connection = _connection(db)
    return await GoogleDriveBrowserService(connection).search(
        workspace.id, q, page_size, page_token
    )


@router.post("/import-image", response_model=GoogleDriveImportResponse)
async def import_image_from_drive(
    data: GoogleDriveImportImageRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = GoogleDriveImportService(db, _connection(db))
    return await service.import_image(data, workspace.id)


@router.post("/import-document", response_model=ProductSourceDocumentResponse)
async def import_document_from_drive(
    data: GoogleDriveImportDocumentRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = GoogleDriveImportService(db, _connection(db))
    return await service.import_document(data, workspace.id, user.id)


@router.post("/import-asset", response_model=GoogleDriveImportResponse)
async def import_asset_from_drive(
    data: GoogleDriveImportAssetRequest,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = GoogleDriveImportService(db, _connection(db))
    return await service.import_asset(data, workspace.id)


@router.get("/documents/{product_id}", response_model=list[ProductSourceDocumentResponse])
async def list_product_documents(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    service = GoogleDriveImportService(db, _connection(db))
    return await service.list_product_documents(product_id, workspace.id)
