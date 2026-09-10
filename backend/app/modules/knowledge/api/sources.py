from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_workspace
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.modules.knowledge.application.sources import KnowledgeSourceService
from app.schemas.knowledge import KnowledgeSourceCreate, KnowledgeSourceResponse, KnowledgeSourceUpdate

router = APIRouter()


def get_knowledge_source_service(
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSourceService:
    return KnowledgeSourceService(db)


@router.get("/", response_model=list[KnowledgeSourceResponse])
async def list_knowledge_sources(
    product_id: Optional[UUID] = Query(None),
    campaign_id: Optional[UUID] = Query(None),
    source_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    workspace: Workspace = Depends(get_current_workspace),
    service: KnowledgeSourceService = Depends(get_knowledge_source_service),
):
    return await service.list(
        workspace.id,
        product_id=product_id,
        campaign_id=campaign_id,
        source_type=source_type,
        status=status,
    )


@router.post("/", response_model=KnowledgeSourceResponse)
async def create_knowledge_source(
    data: KnowledgeSourceCreate,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    service: KnowledgeSourceService = Depends(get_knowledge_source_service),
):
    return await service.create(data, workspace.id, user.id)


@router.get("/{source_id}", response_model=KnowledgeSourceResponse)
async def get_knowledge_source(
    source_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: KnowledgeSourceService = Depends(get_knowledge_source_service),
):
    return await service.get(source_id, workspace.id)


@router.patch("/{source_id}", response_model=KnowledgeSourceResponse)
async def update_knowledge_source(
    source_id: UUID,
    data: KnowledgeSourceUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    service: KnowledgeSourceService = Depends(get_knowledge_source_service),
):
    return await service.update(source_id, data, workspace.id)


@router.delete("/{source_id}")
async def delete_knowledge_source(
    source_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: KnowledgeSourceService = Depends(get_knowledge_source_service),
):
    return await service.delete(source_id, workspace.id)
