from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional

from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.user import User
from app.models.product import Product
from app.models.campaign import Campaign
from app.models.knowledge import KnowledgeSource
from app.schemas.knowledge import (
    KnowledgeSourceCreate, KnowledgeSourceUpdate, KnowledgeSourceResponse,
)
from app.api.deps import get_current_workspace, get_current_user
from app.core.exceptions import NotFoundException, BadRequestException

router = APIRouter()

MAX_SOURCES_PER_ENTITY = 20


@router.get("/", response_model=list[KnowledgeSourceResponse])
async def list_knowledge_sources(
    product_id: Optional[UUID] = Query(None),
    campaign_id: Optional[UUID] = Query(None),
    source_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    query = select(KnowledgeSource).where(KnowledgeSource.workspace_id == workspace.id)
    if product_id:
        query = query.where(KnowledgeSource.product_id == product_id)
    if campaign_id:
        query = query.where(KnowledgeSource.campaign_id == campaign_id)
    if source_type:
        query = query.where(KnowledgeSource.source_type == source_type)
    if status:
        query = query.where(KnowledgeSource.status == status)
    query = query.order_by(KnowledgeSource.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=KnowledgeSourceResponse)
async def create_knowledge_source(
    data: KnowledgeSourceCreate,
    workspace: Workspace = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not data.product_id and not data.campaign_id:
        raise BadRequestException("Either product_id or campaign_id is required")
    if data.product_id and data.campaign_id:
        raise BadRequestException("Cannot specify both product_id and campaign_id")

    if data.product_id:
        product_result = await db.execute(
            select(Product).where(Product.id == data.product_id, Product.workspace_id == workspace.id)
        )
        if not product_result.scalar_one_or_none():
            raise NotFoundException("Product")
        entity_id = data.product_id
        entity_field = "product_id"
    else:
        campaign_result = await db.execute(
            select(Campaign).where(Campaign.id == data.campaign_id, Campaign.workspace_id == workspace.id)
        )
        if not campaign_result.scalar_one_or_none():
            raise NotFoundException("Campaign")
        entity_id = data.campaign_id
        entity_field = "campaign_id"

    # Check source limit
    count_result = await db.execute(
        select(func.count(KnowledgeSource.id)).where(
            KnowledgeSource.workspace_id == workspace.id,
            getattr(KnowledgeSource, entity_field) == entity_id,
        )
    )
    count = count_result.scalar() or 0
    if count >= MAX_SOURCES_PER_ENTITY:
        raise BadRequestException(f"Maximum {MAX_SOURCES_PER_ENTITY} knowledge sources per entity")

    # Compute content hash if content provided
    import hashlib
    content_hash = None
    if data.content_text:
        content_hash = hashlib.sha256(data.content_text.encode()).hexdigest()

    ks = KnowledgeSource(
        workspace_id=workspace.id,
        product_id=data.product_id,
        campaign_id=data.campaign_id,
        source_type=data.source_type,
        content_type=data.content_type,
        title=data.title,
        content_text=data.content_text,
        url=data.url,
        source_document_id=data.source_document_id,
        content_hash=content_hash,
        is_primary=data.is_primary,
        created_by_user_id=user.id,
    )
    db.add(ks)
    await db.flush()
    await db.refresh(ks)
    return ks


@router.get("/{source_id}", response_model=KnowledgeSourceResponse)
async def get_knowledge_source(
    source_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.workspace_id == workspace.id,
        )
    )
    ks = result.scalar_one_or_none()
    if not ks:
        raise NotFoundException("Knowledge source")
    return ks


@router.patch("/{source_id}", response_model=KnowledgeSourceResponse)
async def update_knowledge_source(
    source_id: UUID,
    data: KnowledgeSourceUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.workspace_id == workspace.id,
        )
    )
    ks = result.scalar_one_or_none()
    if not ks:
        raise NotFoundException("Knowledge source")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ks, field, value)

    # Recompute content hash if content changed
    if "content_text" in update_data and ks.content_text:
        import hashlib
        ks.content_hash = hashlib.sha256(ks.content_text.encode()).hexdigest()

    await db.flush()
    await db.refresh(ks)
    return ks


@router.delete("/{source_id}")
async def delete_knowledge_source(
    source_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.workspace_id == workspace.id,
        )
    )
    ks = result.scalar_one_or_none()
    if not ks:
        raise NotFoundException("Knowledge source")
    await db.delete(ks)
    await db.flush()
    return {"deleted": True}
