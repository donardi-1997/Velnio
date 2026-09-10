from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_workspace
from app.core.config import settings
from app.core.exceptions import BadRequestException, InsufficientCreditsException, NotFoundException
from app.db.session import get_db
from app.models.brief import CampaignBrief
from app.models.campaign import Campaign
from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.product import Product
from app.models.workspace import Workspace
from app.services.ai import get_ai_provider
from app.services.knowledge.context_builder import KnowledgeContextBuilder

router = APIRouter()


@router.post("/{campaign_id}/generate-brief")
async def generate_campaign_brief(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign")

    product_result = await db.execute(
        select(Product).where(Product.id == campaign.product_id, Product.workspace_id == workspace.id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise NotFoundException("Product")

    credit_result = await db.execute(
        select(CreditWallet).where(CreditWallet.workspace_id == workspace.id)
    )
    wallet = credit_result.scalar_one_or_none()
    if not wallet or wallet.balance < settings.PLAN_BRIEF_COST:
        raise InsufficientCreditsException()

    knowledge_context = await KnowledgeContextBuilder().build(
        db=db,
        product_id=product.id,
        campaign_id=campaign.id,
        workspace_id=workspace.id,
    )

    wallet.balance -= settings.PLAN_BRIEF_COST
    db.add(
        CreditTransaction(
            workspace_id=workspace.id,
            wallet_id=wallet.id,
            amount=-settings.PLAN_BRIEF_COST,
            transaction_type=TransactionType.USAGE,
            description=f"Campaign brief generation for '{campaign.name}'",
        )
    )
    await db.flush()

    try:
        brief_data = await get_ai_provider().generate_campaign_brief(
            product, campaign, knowledge_context
        )
    except Exception as exc:
        wallet.balance += settings.PLAN_BRIEF_COST
        await db.flush()
        raise BadRequestException(f"Brief generation failed: {str(exc)[:200]}")

    existing_result = await db.execute(
        select(CampaignBrief).where(CampaignBrief.campaign_id == campaign.id)
    )
    brief = existing_result.scalar_one_or_none()
    fields = [
        "product_summary",
        "target_audience",
        "key_benefits",
        "tone_of_voice",
        "pricing_strategy",
        "positioning",
    ]

    if brief:
        for field in fields:
            if field in brief_data:
                setattr(brief, field, brief_data[field])
        brief.generated_at = datetime.now(timezone.utc)
        brief.generated_by_user_id = user.id
        brief.credit_cost = settings.PLAN_BRIEF_COST
    else:
        brief = CampaignBrief(
            campaign_id=campaign.id,
            workspace_id=workspace.id,
            product_summary=brief_data.get("product_summary"),
            target_audience=brief_data.get("target_audience"),
            key_benefits=brief_data.get("key_benefits"),
            tone_of_voice=brief_data.get("tone_of_voice"),
            pricing_strategy=brief_data.get("pricing_strategy"),
            positioning=brief_data.get("positioning"),
            generated_by_user_id=user.id,
            generated_at=datetime.now(timezone.utc),
            credit_cost=settings.PLAN_BRIEF_COST,
        )
        db.add(brief)

    await db.flush()
    await db.refresh(brief)
    return brief
