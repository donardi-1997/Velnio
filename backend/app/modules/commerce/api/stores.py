from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.commerce.application.stores import StoreService
from app.modules.commerce.infrastructure.repository import StoreRepository
from app.schemas.store import MockStoreConnect, StoreResponse

router = APIRouter()


def get_store_service(db: AsyncSession = Depends(get_db)) -> StoreService:
    return StoreService(StoreRepository(db))


@router.get("", response_model=List[StoreResponse])
async def list_stores(
    workspace: Workspace = Depends(get_current_workspace),
    service: StoreService = Depends(get_store_service),
):
    return await service.list(workspace.id)


@router.post("/mock-connect", response_model=StoreResponse, status_code=201)
async def mock_connect(
    data: MockStoreConnect,
    workspace: Workspace = Depends(get_current_workspace),
    service: StoreService = Depends(get_store_service),
):
    return await service.mock_connect(data, workspace.id)


@router.post("/{store_id}/disconnect", response_model=StoreResponse)
async def disconnect_store(
    store_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: StoreService = Depends(get_store_service),
):
    return await service.disconnect(store_id, workspace.id)
