from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, InsufficientCreditsException, NotFoundException
from app.models.brief import CampaignBrief
from app.models.campaign import Campaign
from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.product import Product
from app.services.ai import get_ai_provider
from app.services.knowledge.context_builder import KnowledgeContextBuilder


class CampaignBriefService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate(self, campaign_id: UUID, workspace_id: UUID, user_id: UUID) -> CampaignBrief:
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace_id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise NotFoundException("Campaign")

        result = await self.db.execute(
            select(Product).where(Product.id == campaign.product_id, Product.workspace_id == workspace_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundException("Product")

        result = await self.db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace_id))
        wallet = result.scalar_one_or_none()
        if not wallet or wallet.balance < settings.PLAN_BRIEF_COST:
            raise InsufficientCreditsException()

        knowledge_context = await KnowledgeContextBuilder().build(
            db=self.db,
            product_id=product.id,
            campaign_id=campaign.id,
            workspace_id=workspace_id,
        )

        wallet.balance -= settings.PLAN_BRIEF_COST
        self.db.add(
            CreditTransaction(
                workspace_id=workspace_id,
                wallet_id=wallet.id,
                amount=-settings.PLAN_BRIEF_COST,
                transaction_type=TransactionType.USAGE,
                description=f"Campaign brief generation for '{campaign.name}'",
            )
        )
        await self.db.flush()

        try:
            brief_data = await get_ai_provider().generate_campaign_brief(
                product, campaign, knowledge_context
            )
        except Exception as exc:
            wallet.balance += settings.PLAN_BRIEF_COST
            await self.db.flush()
            raise BadRequestException(f"Brief generation failed: {str(exc)[:200]}")

        result = await self.db.execute(
            select(CampaignBrief).where(CampaignBrief.campaign_id == campaign.id)
        )
        brief = result.scalar_one_or_none()
        fields = (
            "product_summary",
            "target_audience",
            "key_benefits",
            "tone_of_voice",
            "pricing_strategy",
            "positioning",
        )

        if brief:
            for field in fields:
                if field in brief_data:
                    setattr(brief, field, brief_data[field])
            brief.generated_at = datetime.now(timezone.utc)
            brief.generated_by_user_id = user_id
            brief.credit_cost = settings.PLAN_BRIEF_COST
        else:
            brief = CampaignBrief(
                campaign_id=campaign.id,
                workspace_id=workspace_id,
                product_summary=brief_data.get("product_summary"),
                target_audience=brief_data.get("target_audience"),
                key_benefits=brief_data.get("key_benefits"),
                tone_of_voice=brief_data.get("tone_of_voice"),
                pricing_strategy=brief_data.get("pricing_strategy"),
                positioning=brief_data.get("positioning"),
                generated_by_user_id=user_id,
                generated_at=datetime.now(timezone.utc),
                credit_cost=settings.PLAN_BRIEF_COST,
            )
            self.db.add(brief)

        await self.db.flush()
        await self.db.refresh(brief)
        return brief
