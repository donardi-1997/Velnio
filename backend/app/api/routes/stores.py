from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.store import Store, StoreStatus
from app.schemas.store import StoreResponse, MockStoreConnect
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException
from typing import List
from uuid import UUID

router = APIRouter()


@router.get("", response_model=List[StoreResponse])
async def list_stores(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Store).where(Store.workspace_id == workspace.id))
    return result.scalars().all()


@router.post("/mock-connect", response_model=StoreResponse, status_code=201)
async def mock_connect(
    data: MockStoreConnect,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    store = Store(
        workspace_id=workspace.id,
        name=data.name,
        shop_domain=data.shop_domain,
        country=data.country,
        currency=data.currency,
        status=StoreStatus.CONNECTED,
        access_token_encrypted="mock_token",
    )
    db.add(store)
    await db.flush()
    await db.refresh(store)
    return store


@router.post("/{store_id}/disconnect", response_model=StoreResponse)
async def disconnect_store(
    store_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Store).where(Store.id == store_id, Store.workspace_id == workspace.id))
    store = result.scalar_one_or_none()
    if not store:
        raise NotFoundException("Store")
    store.status = StoreStatus.DISCONNECTED
    store.access_token_encrypted = None
    await db.flush()
    await db.refresh(store)
    return store
