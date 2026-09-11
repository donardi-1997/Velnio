from __future__ import annotations

import hashlib
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadGatewayException, BadRequestException, ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.models.campaign import Campaign
from app.models.meta_ads import (
    MetaAdsAdPublication,
    MetaAdsAdSetPublication,
    MetaAdsCampaignPublication,
    MetaAdsCreativePublication,
)
from app.models.workspace import MemberRole, WorkspaceMember
from app.modules.campaigns.application.meta_ads_remote_state import MetaAdsRemoteStateGuard
from app.modules.integrations.application.meta_ads_connection import MetaAdsConnectionService
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError
from app.modules.integrations.infrastructure.meta_ads_ads import get_meta_ads_ad_provider


logger = get_logger(__name__)
META_REQUIRED_SCOPE = "ads_management"


class MetaAdsAdPublishingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.connection_service = MetaAdsConnectionService(db)
        self.remote_state_guard = MetaAdsRemoteStateGuard()

    async def list_ads(
        self,
        campaign_id: UUID,
        publication_id: UUID,
        workspace_id: UUID,
    ) -> list[dict]:
        await self._get_campaign(campaign_id, workspace_id)
        publication = await self._get_publication(campaign_id, publication_id, workspace_id)
        result = await self.db.execute(
            select(MetaAdsAdPublication)
            .where(
                MetaAdsAdPublication.workspace_id == workspace_id,
                MetaAdsAdPublication.campaign_publication_id == publication.id,
            )
            .order_by(MetaAdsAdPublication.created_at.desc())
        )
        return [self._serialize(row) for row in result.scalars().all()]

    async def get_remote_state(
        self,
        campaign_id: UUID,
        publication_id: UUID,
        ad_publication_id: UUID,
        workspace_id: UUID,
    ) -> dict:
        await self._get_campaign(campaign_id, workspace_id)
        publication = await self._get_publication(campaign_id, publication_id, workspace_id)
        ad_set = await self._get_ad_set(publication.id, workspace_id, lock=False)
        ad = await self._get_ad(
            ad_publication_id,
            publication.id,
            ad_set.id,
            workspace_id,
        )
        creative = await self._get_creative(
            ad.creative_publication_id,
            publication.id,
            ad_set.id,
            workspace_id,
        )
        access_token = await self.connection_service.get_valid_token(workspace_id)
        state = await self.remote_state_guard.get_validated_ad_state(
            access_token,
            publication,
            ad_set,
            creative,
            ad,
        )
        return {
            "ad_publication_id": str(ad.id),
            "remote_ad_id": ad.remote_ad_id,
            "account_id": state["account_id"],
            "campaign_id": state["campaign_id"],
            "adset_id": state["adset_id"],
            "creative_id": state["creative_id"],
            "configured_status": state["status"],
            "effective_status": state.get("effective_status"),
        }

    async def publish_paused_ad(
        self,
        campaign_id: UUID,
        publication_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        creative_publication_id: UUID,
    ) -> dict:
        await self._require_admin_membership(workspace_id, user_id)
        campaign = await self._get_campaign(campaign_id, workspace_id)
        publication = await self._get_publication(campaign_id, publication_id, workspace_id)
        ad_set = await self._get_ad_set(publication.id, workspace_id, lock=True)
        creative = await self._get_creative(
            creative_publication_id,
            publication.id,
            ad_set.id,
            workspace_id,
        )

        if publication.remote_status != "PAUSED":
            raise ForbiddenException("Meta campaign must remain PAUSED before creating an Ad")
        if ad_set.remote_status != "PAUSED":
            raise ForbiddenException("Meta Ad Set must remain PAUSED before creating an Ad")

        connection = await self.connection_service.get_active_connection(workspace_id)
        if connection is None:
            raise BadRequestException("Meta Ads not connected")
        self._require_management_scope(connection.scopes)
        access_token = await self.connection_service.get_valid_token(workspace_id)

        accounts = await self.connection_service.list_ad_accounts(workspace_id)
        account = next((item for item in accounts if item.get("id") == publication.ad_account_id), None)
        if account is None:
            raise ForbiddenException("Meta ad account is not accessible from this workspace connection")
        if account.get("account_status") not in {None, 1}:
            raise BadRequestException("Meta ad account is not active")

        await self.remote_state_guard.require_paused_hierarchy(access_token, publication, ad_set)

        idempotency_key = self._idempotency_key(ad_set.id, creative.id)
        existing_result = await self.db.execute(
            select(MetaAdsAdPublication).where(
                MetaAdsAdPublication.workspace_id == workspace_id,
                MetaAdsAdPublication.idempotency_key == idempotency_key,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            payload = self._serialize(existing)
            payload["reused"] = True
            return payload

        name = self._remote_ad_name(campaign, idempotency_key)
        provider = get_meta_ads_ad_provider()
        try:
            remote = await provider.ensure_paused_ad(
                access_token,
                publication.ad_account_id,
                name,
                ad_set.remote_ad_set_id,
                creative.remote_creative_id,
            )
        except MetaAdsProviderError as exc:
            logger.warning("Meta Ads Ad creation failed: %s", type(exc).__name__)
            raise BadGatewayException("Meta Ads Ad creation failed") from exc

        remote_id = remote.get("id")
        if not isinstance(remote_id, str) or not remote_id:
            raise BadGatewayException("Meta Ads returned an invalid Ad response")
        if remote.get("status") != "PAUSED":
            raise BadGatewayException("Meta Ads did not confirm the Ad as PAUSED")

        row = MetaAdsAdPublication(
            workspace_id=workspace_id,
            campaign_publication_id=publication.id,
            ad_set_publication_id=ad_set.id,
            creative_publication_id=creative.id,
            created_by_user_id=user_id,
            idempotency_key=idempotency_key,
            remote_ad_id=remote_id,
            remote_ad_name=name,
            remote_status="PAUSED",
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        payload = self._serialize(row)
        payload["reused"] = bool(remote.get("reused"))
        return payload

    async def _get_campaign(self, campaign_id: UUID, workspace_id: UUID) -> Campaign:
        result = await self.db.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.workspace_id == workspace_id,
            )
        )
        campaign = result.scalar_one_or_none()
        if campaign is None:
            raise NotFoundException("Campaign")
        return campaign

    async def _get_publication(
        self,
        campaign_id: UUID,
        publication_id: UUID,
        workspace_id: UUID,
    ) -> MetaAdsCampaignPublication:
        result = await self.db.execute(
            select(MetaAdsCampaignPublication).where(
                MetaAdsCampaignPublication.id == publication_id,
                MetaAdsCampaignPublication.campaign_id == campaign_id,
                MetaAdsCampaignPublication.workspace_id == workspace_id,
            )
        )
        publication = result.scalar_one_or_none()
        if publication is None:
            raise NotFoundException("Meta Ads campaign publication")
        return publication

    async def _get_ad_set(
        self,
        campaign_publication_id: UUID,
        workspace_id: UUID,
        *,
        lock: bool,
    ) -> MetaAdsAdSetPublication:
        query = select(MetaAdsAdSetPublication).where(
            MetaAdsAdSetPublication.workspace_id == workspace_id,
            MetaAdsAdSetPublication.campaign_publication_id == campaign_publication_id,
        )
        if lock:
            query = query.with_for_update()
        result = await self.db.execute(query)
        ad_set = result.scalar_one_or_none()
        if ad_set is None:
            raise BadRequestException("Create the paused Meta Ad Set before creating an Ad")
        return ad_set

    async def _get_creative(
        self,
        creative_publication_id: UUID,
        campaign_publication_id: UUID,
        ad_set_publication_id: UUID,
        workspace_id: UUID,
    ) -> MetaAdsCreativePublication:
        result = await self.db.execute(
            select(MetaAdsCreativePublication).where(
                MetaAdsCreativePublication.id == creative_publication_id,
                MetaAdsCreativePublication.workspace_id == workspace_id,
                MetaAdsCreativePublication.campaign_publication_id == campaign_publication_id,
                MetaAdsCreativePublication.ad_set_publication_id == ad_set_publication_id,
            )
        )
        creative = result.scalar_one_or_none()
        if creative is None:
            raise NotFoundException("Meta Ads Creative publication")
        return creative

    async def _get_ad(
        self,
        ad_publication_id: UUID,
        campaign_publication_id: UUID,
        ad_set_publication_id: UUID,
        workspace_id: UUID,
    ) -> MetaAdsAdPublication:
        result = await self.db.execute(
            select(MetaAdsAdPublication).where(
                MetaAdsAdPublication.id == ad_publication_id,
                MetaAdsAdPublication.workspace_id == workspace_id,
                MetaAdsAdPublication.campaign_publication_id == campaign_publication_id,
                MetaAdsAdPublication.ad_set_publication_id == ad_set_publication_id,
            )
        )
        ad = result.scalar_one_or_none()
        if ad is None:
            raise NotFoundException("Meta Ads Ad publication")
        return ad

    async def _require_admin_membership(self, workspace_id: UUID, user_id: UUID) -> None:
        result = await self.db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None or member.role not in {MemberRole.OWNER, MemberRole.ADMIN}:
            raise ForbiddenException("Owner or admin role required for Meta Ads publishing")

    @staticmethod
    def _require_management_scope(scopes: str) -> None:
        granted = {part for part in re.split(r"[\s,]+", scopes or "") if part}
        if META_REQUIRED_SCOPE not in granted:
            raise ForbiddenException(
                "Meta Ads connection is read-only; reconnect Meta Ads to grant ads_management before publishing"
            )

    @staticmethod
    def _idempotency_key(ad_set_publication_id: UUID, creative_publication_id: UUID) -> str:
        raw = f"{ad_set_publication_id}:{creative_publication_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _remote_ad_name(campaign: Campaign, idempotency_key: str) -> str:
        marker = f"[VELNIO-AD:{idempotency_key[:16]}]"
        base = (campaign.name or "Velnio campaign").strip() or "Velnio campaign"
        max_base_length = max(1, 500 - len(marker) - 1)
        return f"{base[:max_base_length]} {marker}"

    @staticmethod
    def _serialize(row: MetaAdsAdPublication) -> dict:
        return {
            "id": str(row.id),
            "campaign_publication_id": str(row.campaign_publication_id),
            "ad_set_publication_id": str(row.ad_set_publication_id),
            "creative_publication_id": str(row.creative_publication_id),
            "remote_ad_id": row.remote_ad_id,
            "remote_ad_name": row.remote_ad_name,
            "remote_status": row.remote_status,
            "created_at": row.created_at,
        }
