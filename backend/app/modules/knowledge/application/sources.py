import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.campaign import Campaign
from app.models.knowledge import KnowledgeSource
from app.models.product import Product
from app.modules.knowledge.infrastructure.repository import KnowledgeSourceRepository
from app.schemas.knowledge import KnowledgeSourceCreate, KnowledgeSourceUpdate

MAX_SOURCES_PER_ENTITY = 20


class KnowledgeSourceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = KnowledgeSourceRepository(db)

    async def list(self, workspace_id: UUID, **filters):
        return await self.repository.list(workspace_id, **filters)

    async def get(self, source_id: UUID, workspace_id: UUID) -> KnowledgeSource:
        source = await self.repository.get(source_id, workspace_id)
        if source is None:
            raise NotFoundException("Knowledge source")
        return source

    async def create(
        self,
        data: KnowledgeSourceCreate,
        workspace_id: UUID,
        user_id: UUID,
    ) -> KnowledgeSource:
        if not data.product_id and not data.campaign_id:
            raise BadRequestException("Either product_id or campaign_id is required")
        if data.product_id and data.campaign_id:
            raise BadRequestException("Cannot specify both product_id and campaign_id")

        if data.product_id:
            result = await self.db.execute(
                select(Product).where(Product.id == data.product_id, Product.workspace_id == workspace_id)
            )
            if result.scalar_one_or_none() is None:
                raise NotFoundException("Product")
            count = await self.repository.count_for_product(data.product_id, workspace_id)
        else:
            result = await self.db.execute(
                select(Campaign).where(Campaign.id == data.campaign_id, Campaign.workspace_id == workspace_id)
            )
            if result.scalar_one_or_none() is None:
                raise NotFoundException("Campaign")
            count = await self.repository.count_for_campaign(data.campaign_id, workspace_id)

        if count >= MAX_SOURCES_PER_ENTITY:
            raise BadRequestException(f"Maximum {MAX_SOURCES_PER_ENTITY} knowledge sources per entity")

        content_hash = None
        if data.content_text:
            content_hash = hashlib.sha256(data.content_text.encode()).hexdigest()

        source = KnowledgeSource(
            workspace_id=workspace_id,
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
            created_by_user_id=user_id,
        )
        return await self.repository.add(source)

    async def update(
        self,
        source_id: UUID,
        data: KnowledgeSourceUpdate,
        workspace_id: UUID,
    ) -> KnowledgeSource:
        source = await self.get(source_id, workspace_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(source, field, value)

        if "content_text" in update_data:
            source.content_hash = (
                hashlib.sha256(source.content_text.encode()).hexdigest()
                if source.content_text
                else None
            )
        return await self.repository.flush_and_refresh(source)

    async def delete(self, source_id: UUID, workspace_id: UUID) -> dict:
        source = await self.get(source_id, workspace_id)
        await self.repository.delete(source)
        return {"deleted": True}
