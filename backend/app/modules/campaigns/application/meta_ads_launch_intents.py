from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.meta_ads import MetaAdsAdPublication, MetaAdsLaunchIntent
from app.modules.campaigns.application.meta_ads_launch_readiness import MetaAdsLaunchReadinessService


LAUNCH_INTENT_TTL_MINUTES = 10


class MetaAdsLaunchIntentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.readiness_service = MetaAdsLaunchReadinessService(db)

    async def create_intent(
        self,
        campaign_id: UUID,
        publication_id: UUID,
        ad_publication_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> dict:
        readiness = await self.readiness_service.get_readiness(
            campaign_id,
            publication_id,
            ad_publication_id,
            workspace_id,
            user_id,
        )
        if not readiness.get("ready"):
            raise BadRequestException(
                "Launch readiness must pass before creating a launch intent"
            )

        ad = await self._get_ad(
            ad_publication_id,
            publication_id,
            workspace_id,
        )
        now = datetime.now(timezone.utc)

        previous_result = await self.db.execute(
            select(MetaAdsLaunchIntent)
            .where(
                MetaAdsLaunchIntent.workspace_id == workspace_id,
                MetaAdsLaunchIntent.ad_publication_id == ad.id,
                MetaAdsLaunchIntent.created_by_user_id == user_id,
                MetaAdsLaunchIntent.consumed_at.is_(None),
            )
            .with_for_update()
        )
        for previous in previous_result.scalars().all():
            previous.consumed_at = now
            previous.activation_status = "REPLACED"
            previous.activation_completed_at = now
            previous.last_activation_error = None

        confirmation_token = secrets.token_urlsafe(32)
        token_hash = self.hash_token(confirmation_token)
        expires_at = now + timedelta(minutes=LAUNCH_INTENT_TTL_MINUTES)
        row = MetaAdsLaunchIntent(
            workspace_id=workspace_id,
            campaign_publication_id=ad.campaign_publication_id,
            ad_set_publication_id=ad.ad_set_publication_id,
            creative_publication_id=ad.creative_publication_id,
            ad_publication_id=ad.id,
            created_by_user_id=user_id,
            token_hash=token_hash,
            readiness_fingerprint=readiness["readiness_fingerprint"],
            expires_at=expires_at,
            consumed_at=None,
            activation_status="PENDING_CONFIRMATION",
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)

        return {
            "id": str(row.id),
            "ad_publication_id": str(row.ad_publication_id),
            "readiness_fingerprint": row.readiness_fingerprint,
            "confirmation_token": confirmation_token,
            "expires_at": row.expires_at,
            "created_at": row.created_at,
            "status": "PENDING_CONFIRMATION",
            "side_effects_performed": False,
        }

    async def _get_ad(
        self,
        ad_publication_id: UUID,
        publication_id: UUID,
        workspace_id: UUID,
    ) -> MetaAdsAdPublication:
        result = await self.db.execute(
            select(MetaAdsAdPublication).where(
                MetaAdsAdPublication.id == ad_publication_id,
                MetaAdsAdPublication.workspace_id == workspace_id,
                MetaAdsAdPublication.campaign_publication_id == publication_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundException("Meta Ads Ad publication")
        return row

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
