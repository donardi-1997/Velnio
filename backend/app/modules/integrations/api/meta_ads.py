from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_workspace
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.modules.integrations.application.meta_ads_connection import MetaAdsConnectionService


router = APIRouter()


class MetaAdsStatus(BaseModel):
    connected: bool
    expired: bool = False
    mode: str
    meta_user_id: str | None = None
    meta_user_name: str | None = None
    connected_at: datetime | None = None
    expires_at: datetime | None = None


class MetaAdAccount(BaseModel):
    id: str
    account_id: str
    name: str
    account_status: int | None = None
    currency: str | None = None
    timezone_name: str | None = None


def _service(db: AsyncSession) -> MetaAdsConnectionService:
    return MetaAdsConnectionService(db)


@router.get("/status", response_model=MetaAdsStatus)
async def get_meta_ads_status(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    status = await _service(db).status(workspace.id)
    return {**status, "mode": settings.META_ADS_MODE}


@router.get("/connect")
async def connect_meta_ads(
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _service(db).auth_url(workspace.id, user.id)


@router.get("/callback")
async def handle_meta_ads_callback(
    state: str = Query(...),
    code: str | None = Query(None),
    error: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = _service(db)
    workspace_id, user_id = await service.validate_oauth_state(state)
    if error or not code:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings?meta_ads=denied")
    await service.connect_from_code(workspace_id, user_id, code)
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings?meta_ads=connected")


@router.post("/connect-mock")
async def connect_meta_ads_mock(
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _service(db).connect_mock(workspace.id, user.id)


@router.post("/disconnect")
async def disconnect_meta_ads(
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _service(db).disconnect(workspace.id, user.id)


@router.get("/ad-accounts", response_model=list[MetaAdAccount])
async def list_meta_ad_accounts(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await _service(db).list_ad_accounts(workspace.id)
