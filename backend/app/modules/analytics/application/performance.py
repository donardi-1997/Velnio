from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, InsufficientCreditsException, NotFoundException
from app.core.logging import get_logger
from app.models.campaign import Campaign
from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.tracking import CampaignPerformanceInsight, LandingVariant
from app.services.ai import get_ai_provider
from app.services.metrics import CampaignMetricsService

logger = get_logger(__name__)


class PerformanceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.metrics = CampaignMetricsService(db)

    async def _campaign(self, campaign_id: UUID, workspace_id: UUID) -> Campaign:
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace_id)
        )
        campaign = result.scalar_one_or_none()
        if campaign is None:
            raise NotFoundException("Campaign")
        return campaign

    @staticmethod
    def parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    async def get_performance(self, campaign_id: UUID, workspace_id: UUID, from_date=None, to_date=None):
        campaign = await self._campaign(campaign_id, workspace_id)
        metrics = await self.metrics.get_campaign_metrics(
            campaign_id, self.parse_date(from_date), self.parse_date(to_date)
        )
        return {**metrics, "currency": campaign.currency or "USD"}

    async def get_timeline(self, campaign_id: UUID, workspace_id: UUID, from_date=None, to_date=None):
        await self._campaign(campaign_id, workspace_id)
        timeline = await self.metrics.get_campaign_timeline(
            campaign_id, self.parse_date(from_date), self.parse_date(to_date)
        )
        return {"timeline": timeline}

    async def get_variant_performance(self, campaign_id: UUID, workspace_id: UUID):
        await self._campaign(campaign_id, workspace_id)
        metrics = await self.metrics.get_variant_metrics(campaign_id)
        enriched = []
        for item in metrics:
            variant_id = item.get("variant_id")
            if variant_id:
                result = await self.db.execute(select(LandingVariant).where(LandingVariant.id == UUID(variant_id)))
                variant = result.scalar_one_or_none()
                item["variant_name"] = variant.name if variant else "Unknown"
                item["variant_key"] = variant.variant_key if variant else "?"
                item["status"] = variant.status if variant else "unknown"
                item["traffic_weight"] = variant.traffic_weight if variant else 0
            enriched.append(item)
        return {"variants": enriched}

    async def get_angle_performance(self, campaign_id: UUID, workspace_id: UUID):
        await self._campaign(campaign_id, workspace_id)
        return {"angles": await self.metrics.get_angle_metrics(campaign_id)}

    async def analyze(self, campaign_id: UUID, workspace_id: UUID):
        campaign = await self._campaign(campaign_id, workspace_id)
        metrics = await self.metrics.get_campaign_metrics(campaign_id)
        if metrics["sessions"] < 50:
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient data: {metrics['sessions']} sessions (need 50)",
            )

        wallet_result = await self.db.execute(
            select(CreditWallet).where(CreditWallet.workspace_id == workspace_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        if wallet is None or wallet.balance < settings.PLAN_PERFORMANCE_ANALYSIS_COST:
            raise InsufficientCreditsException()

        variant_metrics = await self.metrics.get_variant_metrics(campaign_id)
        angle_metrics = await self.metrics.get_angle_metrics(campaign_id)

        try:
            data = await get_ai_provider().analyze_campaign_performance(
                campaign=campaign,
                metrics=metrics,
                variants=variant_metrics,
                angles=angle_metrics,
            )
            insight = CampaignPerformanceInsight(
                campaign_id=campaign_id,
                summary=data.get("summary", ""),
                winning_pattern=data.get("winning_pattern"),
                weak_points=data.get("weak_points", []),
                recommended_actions=data.get("recommended_actions", []),
                next_test_type=data.get("next_test_type"),
                next_test_hypothesis=data.get("next_test_hypothesis"),
                confidence=data.get("confidence"),
                based_on_sessions=metrics["sessions"],
                generated_at=datetime.now(timezone.utc),
            )
            self.db.add(insight)
            wallet.balance -= settings.PLAN_PERFORMANCE_ANALYSIS_COST
            self.db.add(CreditTransaction(
                workspace_id=workspace_id,
                wallet_id=wallet.id,
                amount=-settings.PLAN_PERFORMANCE_ANALYSIS_COST,
                transaction_type=TransactionType.USAGE,
                description="Performance analysis",
                reference_type="campaign_performance",
                reference_id=campaign_id,
            ))
            await self.db.flush()
            await self.db.refresh(insight)
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
        except (InsufficientCreditsException, HTTPException):
            raise
        except Exception as exc:
            logger.error(f"Performance analysis failed: {exc}")
            raise BadRequestException("Performance analysis failed. Please try again.")
