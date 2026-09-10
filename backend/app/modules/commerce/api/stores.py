from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_current_workspace,
    get_current_workspace_member,
)
from app.core.config import settings
from app.core.exceptions import ForbiddenException
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import MemberRole, Workspace, WorkspaceMember
from app.modules.commerce.application.shopify_connection import ShopifyConnectionService
from app.modules.commerce.application.stores import StoreService
from app.modules.commerce.infrastructure.repository import StoreRepository
from app.schemas.store import MockStoreConnect, ShopifyConnectRequest, ShopifyConnectResponse, StoreResponse

router = APIRouter()


def get_store_service(db: AsyncSession = Depends(get_db)) -> StoreService:
    return StoreService(StoreRepository(db))


def get_shopify_connection_service(db: AsyncSession = Depends(get_db)) -> ShopifyConnectionService:
    return ShopifyConnectionService(db)


def require_store_admin(
    member: WorkspaceMember = Depends(get_current_workspace_member),
) -> WorkspaceMember:
    if member.role not in {MemberRole.OWNER, MemberRole.ADMIN}:
        raise ForbiddenException("Only workspace owners and admins can manage stores")
    return member


@router.get("", response_model=List[StoreResponse])
async def list_stores(
    workspace: Workspace = Depends(get_current_workspace),
    service: StoreService = Depends(get_store_service),
):
    return await service.list(workspace.id)


@router.post("/shopify/connect", response_model=ShopifyConnectResponse)
async def connect_shopify(
    data: ShopifyConnectRequest,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    _: WorkspaceMember = Depends(require_store_admin),
    service: ShopifyConnectionService = Depends(get_shopify_connection_service),
):
    return await service.start(workspace.id, user.id, data.shop_domain)


@router.get("/shopify/callback", include_in_schema=False)
async def shopify_callback(
    request: Request,
    service: ShopifyConnectionService = Depends(get_shopify_connection_service),
):
    await service.complete(dict(request.query_params))
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL.rstrip('/')}/stores?shopify=connected",
        status_code=302,
    )


@router.post("/mock-connect", response_model=StoreResponse, status_code=201)
async def mock_connect(
    data: MockStoreConnect,
    workspace: Workspace = Depends(get_current_workspace),
    _: WorkspaceMember = Depends(require_store_admin),
    service: StoreService = Depends(get_store_service),
):
    return await service.mock_connect(data, workspace.id)


@router.post("/{store_id}/disconnect", response_model=StoreResponse)
async def disconnect_store(
    store_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    _: WorkspaceMember = Depends(require_store_admin),
    service: StoreService = Depends(get_store_service),
):
    return await service.disconnect(store_id, workspace.id)
