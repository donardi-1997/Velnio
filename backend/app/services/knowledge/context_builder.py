"""Builds AI context from knowledge sources, respecting character limits."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_AI_CONTEXT_CHARS = 50000


class KnowledgeContextBuilder:
    """Assembles knowledge sources into a single text block for AI consumption."""

    async def build(
        self,
        db: AsyncSession,
        product_id: Optional[UUID] = None,
        campaign_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
        max_chars: int = MAX_AI_CONTEXT_CHARS,
    ) -> str:
        """Build context string from active knowledge sources."""
        from app.models.knowledge import KnowledgeSource

        query = select(KnowledgeSource).where(
            KnowledgeSource.workspace_id == workspace_id,
            KnowledgeSource.status == "ACTIVE",
        )
        if product_id:
            query = query.where(KnowledgeSource.product_id == product_id)
        if campaign_id:
            query = query.where(KnowledgeSource.campaign_id == campaign_id)

        result = await db.execute(query)
        sources = result.scalars().all()

        if not sources:
            return ""

        sections = []
        total_chars = 0

        # Prioritize primary sources first
        primary = [s for s in sources if s.is_primary]
        secondary = [s for s in sources if not s.is_primary]

        for source in primary + secondary:
            text = source.content_text or ""
            if not text:
                continue

            header = f"[{source.source_type}] {source.title}: "
            overhead = len(header) + 4  # 4 for "\n\n" separator + margin

            if total_chars + overhead >= max_chars:
                break

            available = max_chars - total_chars - overhead
            if len(text) > available:
                text = text[:available] + "..."

            section = header + text
            sections.append(section)
            total_chars += len(section)

        return "\n\n".join(sections)
