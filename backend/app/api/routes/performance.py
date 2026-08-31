from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.campaign import Campaign
from app.models.tracking import LandingVariant, CampaignPerformanceInsight
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException, InsufficientCreditsException, BadRequestException
from app.core.config import settings
from app.core.logging import get_logger
from app.services.metrics import CampaignMetricsService
from app.services.experiments import ExperimentAnalysisService
from app.services.ai import get_ai_provider
from app.models.credit import CreditWallet, CreditTransaction, TransactionType
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone

logger = get_logger(__name__)
router = APIRouter()


class PerformanceResponse(BaseModel):
    visitors: int = 0
    sessions: int = 0
    page_views: int = 0
    cta_clicks: int = 0
    add_to_carts: int = 0
    checkouts: int = 0
    purchases: int = 0
    revenue: float = 0.0
    currency: str = "USD"
    ctr: float = 0.0
    atc_rate: float = 0.0
    checkout_rate: float = 0.0
    conversion_rate: float = 0.0
    revenue_per_visitor: float = 0.0
    aov: float = 0.0


@router.get("/{campaign_id}/performance")
async def get_performance(
    campaign_id: UUID,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign")

    parsed_from = None
    parsed_to = None
    if from_date:
        try:
            parsed_from = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
        except ValueError:
            pass
    if to_date:
        try:
            parsed_to = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
        except ValueError:
            pass

    metrics_service = CampaignMetricsService(db)
    metrics = await metrics_service.get_campaign_metrics(campaign_id, parsed_from, parsed_to)

    return {
        **metrics,
        "currency": campaign.currency or "USD",
    }


@router.get("/{campaign_id}/performance/timeline")
async def get_performance_timeline(
    campaign_id: UUID,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign")

    parsed_from = None
    parsed_to = None
    if from_date:
        try:
            parsed_from = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
        except ValueError:
            pass
    if to_date:
        try:
            parsed_to = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
        except ValueError:
            pass

    metrics_service = CampaignMetricsService(db)
    timeline = await metrics_service.get_campaign_timeline(campaign_id, parsed_from, parsed_to)

    return {"timeline": timeline}


@router.get("/{campaign_id}/variants/performance")
async def get_variant_performance(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign")

    metrics_service = CampaignMetricsService(db)
    metrics = await metrics_service.get_variant_metrics(campaign_id)

    # Enrich with variant info
    enriched = []
    for m in metrics:
        variant_id = m.get("variant_id")
        if variant_id:
            v_result = await db.execute(
                select(LandingVariant).where(LandingVariant.id == UUID(variant_id))
            )
            variant = v_result.scalar_one_or_none()
            m["variant_name"] = variant.name if variant else "Unknown"
            m["variant_key"] = variant.variant_key if variant else "?"
            m["status"] = variant.status if variant else "unknown"
            m["traffic_weight"] = variant.traffic_weight if variant else 0
        enriched.append(m)

    return {"variants": enriched}


@router.get("/{campaign_id}/angles/performance")
async def get_angle_performance(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign")

    metrics_service = CampaignMetricsService(db)
    metrics = await metrics_service.get_angle_metrics(campaign_id)

    return {"angles": metrics}


@router.post("/{campaign_id}/performance/analyze")
async def analyze_performance(
    campaign_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign")

    # Check minimum sessions
    metrics_service = CampaignMetricsService(db)
    metrics = await metrics_service.get_campaign_metrics(campaign_id)

    if metrics["sessions"] < 50:
        raise HTTPException(status_code=409, detail=f"Insufficient data: {metrics['sessions']} sessions (need 50)")

    # Check credits
    wallet_result = await db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace.id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet or wallet.balance < settings.PLAN_PERFORMANCE_ANALYSIS_COST:
        raise InsufficientCreditsException()

    # Get variant and angle metrics for context
    variant_metrics = await metrics_service.get_variant_metrics(campaign_id)
    angle_metrics = await metrics_service.get_angle_metrics(campaign_id)

    try:
        ai = get_ai_provider()
        insight_data = await ai.analyze_campaign_performance(
            campaign=campaign,
            metrics=metrics,
            variants=variant_metrics,
            angles=angle_metrics,
        )

        insight = CampaignPerformanceInsight(
            campaign_id=campaign_id,
            summary=insight_data.get("summary", ""),
            winning_pattern=insight_data.get("winning_pattern"),
            weak_points=insight_data.get("weak_points", []),
            recommended_actions=insight_data.get("recommended_actions", []),
            next_test_type=insight_data.get("next_test_type"),
            next_test_hypothesis=insight_data.get("next_test_hypothesis"),
            confidence=insight_data.get("confidence"),
            based_on_sessions=metrics["sessions"],
            generated_at=datetime.now(timezone.utc),
        )
        db.add(insight)

        # Deduct credits
        wallet.balance -= settings.PLAN_PERFORMANCE_ANALYSIS_COST
        tx = CreditTransaction(
            workspace_id=workspace.id,
            wallet_id=wallet.id,
            amount=-settings.PLAN_PERFORMANCE_ANALYSIS_COST,
            transaction_type=TransactionType.USAGE,
            description="Performance analysis",
            reference_type="campaign_performance",
            reference_id=campaign_id,
        )
        db.add(tx)

        await db.flush()
        await db.refresh(insight)

        return {
            "id": str(insight.id),
            "campaign_id": str(insight.campaign_id),
            "summary": insight.summary,
            "winning_pattern": insight.winning_pattern,
            "weak_points": insight.weak_points,
            "recommended_actions": insight.recommended_actions,
            "next_test_type": insight.next_test_type,
            "next_test_hypothesis": insight.next_test_hypothesis,
            "confidence": insight.confidence,
            "based_on_sessions": insight.based_on_sessions,
            "generated_at": insight.generated_at.isoformat() if insight.generated_at else None,
        }

    except Exception as e:
        logger.error(f"Performance analysis failed: {e}")
        raise BadRequestException("Performance analysis failed. Please try again.")



