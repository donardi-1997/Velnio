import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadGatewayException, BadRequestException, ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.models.campaign import Campaign
from app.models.meta_ads import MetaAdsCampaignPublication
from app.models.workspace import MemberRole, WorkspaceMember
from app.modules.integrations.application.meta_ads_connection import MetaAdsConnectionService
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError, get_meta_ads_provider


logger = get_logger(__name__)
META_CAMPAIGN_OBJECTIVE = "OUTCOME_SALES"
META_REQUIRED_SCOPE = "ads_management"


class MetaAdsCampaignPublishingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.connection_service = MetaAdsConnectionService(db)

    async def list_publications(self, campaign_id: UUID, workspace_id: UUID) -> list[dict]:
        await self._get_campaign(campaign_id, workspace_id, lock=False)
        result = await self.db.execute(
            select(MetaAdsCampaignPublication)
            .where(
                MetaAdsCampaignPublication.campaign_id == campaign_id,
                MetaAdsCampaignPublication.workspace_id == workspace_id,
            )
            .order_by(MetaAdsCampaignPublication.created_at.asc())
        )
        return [self._serialize(row) for row in result.scalars().all()]

    async def publish_paused_campaign(
        self,
        campaign_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        ad_account_id: str,
    ) -> dict:
        await self._require_admin_membership(workspace_id, user_id)
        campaign = await self._get_campaign(campaign_id, workspace_id, lock=True)

        connection = await self.connection_service.get_active_connection(workspace_id)
        if connection is None:
            raise BadRequestException("Meta Ads not connected")
        self._require_management_scope(connection.scopes)
        access_token = await self.connection_service.get_valid_token(workspace_id)

        accounts = await self.connection_service.list_ad_accounts(workspace_id)
        selected_account = next((item for item in accounts if item.get("id") == ad_account_id), None)
        if selected_account is None:
            raise ForbiddenException("Meta ad account is not accessible from this workspace connection")
        if selected_account.get("account_status") not in {None, 1}:
            raise BadRequestException("Meta ad account is not active")

        existing_result = await self.db.execute(
            select(MetaAdsCampaignPublication).where(
                MetaAdsCampaignPublication.workspace_id == workspace_id,
                MetaAdsCampaignPublication.campaign_id == campaign_id,
                MetaAdsCampaignPublication.ad_account_id == ad_account_id,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            payload = self._serialize(existing)
            payload["reused"] = True
            return payload

        remote_name = self._remote_campaign_name(campaign)
        provider = get_meta_ads_provider()
        try:
            remote = await provider.ensure_paused_campaign(
                access_token,
                ad_account_id,
                remote_name,
                META_CAMPAIGN_OBJECTIVE,
            )
        except MetaAdsProviderError as exc:
            logger.warning("Meta Ads campaign creation failed: %s", type(exc).__name__)
            raise BadGatewayException("Meta Ads campaign creation failed") from exc

        remote_id = remote.get("id")
        if not isinstance(remote_id, str) or not remote_id:
            raise BadGatewayException("Meta Ads returned an invalid campaign response")
        remote_status = remote.get("status")
        if not isinstance(remote_status, str) or not remote_status:
            remote_status = "UNKNOWN"

        publication = MetaAdsCampaignPublication(
            workspace_id=workspace_id,
            campaign_id=campaign_id,
            created_by_user_id=user_id,
            ad_account_id=ad_account_id,
            remote_campaign_id=remote_id,
            remote_campaign_name=remote_name,
            objective=META_CAMPAIGN_OBJECTIVE,
            remote_status=remote_status,
        )
        self.db.add(publication)
        await self.db.flush()
        await self.db.refresh(publication)
        payload = self._serialize(publication)
        payload["reused"] = bool(remote.get("reused"))
        return payload

    async def _get_campaign(self, campaign_id: UUID, workspace_id: UUID, *, lock: bool) -> Campaign:
        query = select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.workspace_id == workspace_id,
        )
        if lock:
            query = query.with_for_update()
        result = await self.db.execute(query)
        campaign = result.scalar_one_or_none()
        if campaign is None:
            raise NotFoundException("Campaign")
        return campaign

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
    def _remote_campaign_name(campaign: Campaign) -> str:
        marker = f"[VELNIO:{campaign.id}]"
        base = (campaign.name or "Velnio campaign").strip() or "Velnio campaign"
        max_base_length = max(1, 500 - len(marker) - 1)
        return f"{base[:max_base_length]} {marker}"

    @staticmethod
    def _serialize(publication: MetaAdsCampaignPublication) -> dict:
        return {
            "id": str(publication.id),
            "campaign_id": str(publication.campaign_id),
            "ad_account_id": publication.ad_account_id,
            "remote_campaign_id": publication.remote_campaign_id,
            "remote_campaign_name": publication.remote_campaign_name,
            "objective": publication.objective,
            "remote_status": publication.remote_status,
            "created_at": publication.created_at,
        }
