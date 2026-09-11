from __future__ import annotations

import hmac
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BadGatewayException,
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.core.logging import get_logger
from app.models.meta_ads import (
    MetaAdsAdPublication,
    MetaAdsAdSetPublication,
    MetaAdsCampaignPublication,
    MetaAdsCreativePublication,
    MetaAdsLaunchIntent,
)
from app.modules.campaigns.application.meta_ads_launch_intents import MetaAdsLaunchIntentService
from app.modules.campaigns.application.meta_ads_launch_readiness import MetaAdsLaunchReadinessService
from app.modules.integrations.application.meta_ads_connection import MetaAdsConnectionService
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError
from app.modules.integrations.infrastructure.meta_ads_activation import get_meta_ads_activation_provider


logger = get_logger(__name__)


class MetaAdsLaunchConfirmationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.readiness_service = MetaAdsLaunchReadinessService(db)
        self.connection_service = MetaAdsConnectionService(db)

    async def confirm_launch(
        self,
        campaign_id: UUID,
        publication_id: UUID,
        ad_publication_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        intent_id: UUID,
        confirmation_token: str,
        acknowledged_readiness_fingerprint: str,
        acknowledged_daily_budget_minor: int,
    ) -> dict:
        intent = await self._get_intent_for_update(
            intent_id,
            publication_id,
            ad_publication_id,
            workspace_id,
            user_id,
        )
        now = datetime.now(timezone.utc)
        self._validate_intent(intent, confirmation_token, now)

        mode = settings.META_ADS_MODE.lower().strip()
        if mode == "real" and not settings.META_ADS_LAUNCH_ENABLED:
            raise ForbiddenException(
                "Real Meta Ads launch is disabled by server configuration"
            )

        readiness = await self.readiness_service.get_readiness(
            campaign_id,
            publication_id,
            ad_publication_id,
            workspace_id,
            user_id,
        )
        if not readiness.get("ready"):
            raise BadRequestException(
                "Launch readiness changed; run the preflight again and create a new launch intent"
            )
        current_fingerprint = readiness.get("readiness_fingerprint")
        if not isinstance(current_fingerprint, str) or not hmac.compare_digest(
            current_fingerprint,
            intent.readiness_fingerprint,
        ):
            raise BadRequestException(
                "Launch readiness changed; create a new launch intent"
            )
        if not hmac.compare_digest(
            acknowledged_readiness_fingerprint,
            intent.readiness_fingerprint,
        ):
            raise BadRequestException("Launch confirmation fingerprint does not match the intent")

        current_budget = readiness["launch_plan"]["daily_budget_minor"]
        if acknowledged_daily_budget_minor != current_budget:
            raise BadRequestException(
                "Acknowledged daily budget no longer matches the launch plan"
            )

        publication, ad_set, creative, ad = await self._get_hierarchy(
            campaign_id,
            publication_id,
            ad_publication_id,
            intent,
            workspace_id,
        )

        # Durable one-shot boundary: this commit happens before any external Meta write.
        intent.consumed_at = now
        intent.activation_status = "ACTIVATING"
        intent.activation_started_at = now
        intent.activation_completed_at = None
        intent.last_activation_error = None
        await self.db.commit()

        external_started = False
        try:
            connection = await self.connection_service.get_active_connection(workspace_id)
            if connection is None:
                raise BadRequestException("Meta Ads not connected")
            access_token = await self.connection_service.get_valid_token(workspace_id)
            provider = get_meta_ads_activation_provider()

            external_started = True
            ad_state = await provider.set_ad_status(
                access_token,
                publication.ad_account_id,
                publication.remote_campaign_id,
                ad_set.remote_ad_set_id,
                creative.remote_creative_id,
                ad.remote_ad_id,
                "ACTIVE",
                expected_status="PAUSED",
            )
            self._require_status(ad_state, "ACTIVE", "Ad")
            ad.remote_status = "ACTIVE"
            await self.db.commit()

            ad_set_state = await provider.set_ad_set_status(
                access_token,
                publication.ad_account_id,
                publication.remote_campaign_id,
                ad_set.remote_ad_set_id,
                "ACTIVE",
                expected_status="PAUSED",
            )
            self._require_status(ad_set_state, "ACTIVE", "Ad Set")
            ad_set.remote_status = "ACTIVE"
            await self.db.commit()

            campaign_state = await provider.set_campaign_status(
                access_token,
                publication.ad_account_id,
                publication.remote_campaign_id,
                "ACTIVE",
                expected_status="PAUSED",
            )
            self._require_status(campaign_state, "ACTIVE", "Campaign")
            publication.remote_status = "ACTIVE"
            intent.activation_status = "SUCCEEDED"
            intent.activation_completed_at = datetime.now(timezone.utc)
            intent.last_activation_error = None
            await self.db.commit()

            return {
                "intent_id": str(intent.id),
                "status": "SUCCEEDED",
                "remote_campaign_status": "ACTIVE",
                "remote_ad_set_status": "ACTIVE",
                "remote_ad_status": "ACTIVE",
                "daily_budget_minor": current_budget,
                "currency": readiness["launch_plan"]["currency"],
                "target_country": readiness["launch_plan"]["target_country"],
                "destination_url": readiness["launch_plan"]["destination_url"],
                "activated_at": intent.activation_completed_at,
            }
        except Exception as exc:
            if isinstance(exc, (BadRequestException, ForbiddenException)) and not external_started:
                await self._record_failure(
                    intent,
                    "FAILED",
                    "Launch stopped before any Meta status write",
                )
                raise

            logger.warning("Meta Ads launch failed: %s", type(exc).__name__)
            safely_paused = False
            if external_started:
                safely_paused = await self._best_effort_pause_hierarchy(
                    workspace_id,
                    publication,
                    ad_set,
                    creative,
                    ad,
                )

            if safely_paused:
                await self._record_failure(
                    intent,
                    "FAILED",
                    "Meta Ads launch failed; hierarchy was restored to PAUSED",
                )
                raise BadGatewayException(
                    "Meta Ads launch failed; Campaign, Ad Set and Ad were restored to PAUSED"
                ) from exc

            await self._record_failure(
                intent,
                "UNKNOWN",
                "Meta Ads launch failed and rollback could not be fully verified",
            )
            raise BadGatewayException(
                "Meta Ads launch state is uncertain; check Meta Ads Manager immediately"
            ) from exc

    async def _best_effort_pause_hierarchy(
        self,
        workspace_id: UUID,
        publication: MetaAdsCampaignPublication,
        ad_set: MetaAdsAdSetPublication,
        creative: MetaAdsCreativePublication,
        ad: MetaAdsAdPublication,
    ) -> bool:
        try:
            access_token = await self.connection_service.get_valid_token(workspace_id)
            provider = get_meta_ads_activation_provider()
        except Exception as exc:
            logger.error("Meta Ads rollback could not initialize: %s", type(exc).__name__)
            return False

        all_paused = True

        # Parent first: if Campaign activation was ambiguous, pause it before touching children.
        try:
            state = await provider.set_campaign_status(
                access_token,
                publication.ad_account_id,
                publication.remote_campaign_id,
                "PAUSED",
            )
            self._require_status(state, "PAUSED", "Campaign")
            publication.remote_status = "PAUSED"
            await self.db.commit()
        except Exception as exc:
            logger.error("Meta Ads Campaign rollback failed: %s", type(exc).__name__)
            all_paused = False

        try:
            state = await provider.set_ad_set_status(
                access_token,
                publication.ad_account_id,
                publication.remote_campaign_id,
                ad_set.remote_ad_set_id,
                "PAUSED",
            )
            self._require_status(state, "PAUSED", "Ad Set")
            ad_set.remote_status = "PAUSED"
            await self.db.commit()
        except Exception as exc:
            logger.error("Meta Ads Ad Set rollback failed: %s", type(exc).__name__)
            all_paused = False

        try:
            state = await provider.set_ad_status(
                access_token,
                publication.ad_account_id,
                publication.remote_campaign_id,
                ad_set.remote_ad_set_id,
                creative.remote_creative_id,
                ad.remote_ad_id,
                "PAUSED",
            )
            self._require_status(state, "PAUSED", "Ad")
            ad.remote_status = "PAUSED"
            await self.db.commit()
        except Exception as exc:
            logger.error("Meta Ads Ad rollback failed: %s", type(exc).__name__)
            all_paused = False

        return all_paused

    async def _record_failure(
        self,
        intent: MetaAdsLaunchIntent,
        status: str,
        message: str,
    ) -> None:
        intent.activation_status = status
        intent.activation_completed_at = datetime.now(timezone.utc)
        intent.last_activation_error = message
        await self.db.commit()

    async def _get_intent_for_update(
        self,
        intent_id: UUID,
        publication_id: UUID,
        ad_publication_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> MetaAdsLaunchIntent:
        result = await self.db.execute(
            select(MetaAdsLaunchIntent)
            .where(
                MetaAdsLaunchIntent.id == intent_id,
                MetaAdsLaunchIntent.workspace_id == workspace_id,
                MetaAdsLaunchIntent.campaign_publication_id == publication_id,
                MetaAdsLaunchIntent.ad_publication_id == ad_publication_id,
                MetaAdsLaunchIntent.created_by_user_id == user_id,
            )
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundException("Meta Ads launch intent")
        return row

    def _validate_intent(
        self,
        intent: MetaAdsLaunchIntent,
        confirmation_token: str,
        now: datetime,
    ) -> None:
        if intent.consumed_at is not None or intent.activation_status != "PENDING_CONFIRMATION":
            raise BadRequestException("Meta Ads launch intent has already been consumed")
        expires_at = intent.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise BadRequestException("Meta Ads launch intent has expired")
        token_hash = MetaAdsLaunchIntentService.hash_token(confirmation_token)
        if not hmac.compare_digest(token_hash, intent.token_hash):
            raise ForbiddenException("Invalid Meta Ads launch confirmation token")

    async def _get_hierarchy(
        self,
        campaign_id: UUID,
        publication_id: UUID,
        ad_publication_id: UUID,
        intent: MetaAdsLaunchIntent,
        workspace_id: UUID,
    ) -> tuple[
        MetaAdsCampaignPublication,
        MetaAdsAdSetPublication,
        MetaAdsCreativePublication,
        MetaAdsAdPublication,
    ]:
        pub_result = await self.db.execute(
            select(MetaAdsCampaignPublication).where(
                MetaAdsCampaignPublication.id == publication_id,
                MetaAdsCampaignPublication.campaign_id == campaign_id,
                MetaAdsCampaignPublication.workspace_id == workspace_id,
            )
        )
        publication = pub_result.scalar_one_or_none()
        if publication is None:
            raise NotFoundException("Meta Ads campaign publication")

        ad_set_result = await self.db.execute(
            select(MetaAdsAdSetPublication).where(
                MetaAdsAdSetPublication.id == intent.ad_set_publication_id,
                MetaAdsAdSetPublication.workspace_id == workspace_id,
                MetaAdsAdSetPublication.campaign_publication_id == publication.id,
            )
        )
        ad_set = ad_set_result.scalar_one_or_none()
        if ad_set is None:
            raise NotFoundException("Meta Ads Ad Set publication")

        creative_result = await self.db.execute(
            select(MetaAdsCreativePublication).where(
                MetaAdsCreativePublication.id == intent.creative_publication_id,
                MetaAdsCreativePublication.workspace_id == workspace_id,
                MetaAdsCreativePublication.campaign_publication_id == publication.id,
                MetaAdsCreativePublication.ad_set_publication_id == ad_set.id,
            )
        )
        creative = creative_result.scalar_one_or_none()
        if creative is None:
            raise NotFoundException("Meta Ads Creative publication")

        ad_result = await self.db.execute(
            select(MetaAdsAdPublication).where(
                MetaAdsAdPublication.id == ad_publication_id,
                MetaAdsAdPublication.id == intent.ad_publication_id,
                MetaAdsAdPublication.workspace_id == workspace_id,
                MetaAdsAdPublication.campaign_publication_id == publication.id,
                MetaAdsAdPublication.ad_set_publication_id == ad_set.id,
                MetaAdsAdPublication.creative_publication_id == creative.id,
            )
        )
        ad = ad_result.scalar_one_or_none()
        if ad is None:
            raise NotFoundException("Meta Ads Ad publication")
        return publication, ad_set, creative, ad

    @staticmethod
    def _require_status(state: dict, expected: str, resource: str) -> None:
        if state.get("status") != expected:
            raise MetaAdsProviderError(f"Meta did not confirm {resource} status")
