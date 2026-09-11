import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadGatewayException, BadRequestException, ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.models.campaign import Campaign
from app.models.meta_ads import MetaAdsAdSetPublication, MetaAdsCampaignPublication
from app.models.workspace import MemberRole, WorkspaceMember
from app.modules.integrations.application.meta_ads_connection import MetaAdsConnectionService
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError, get_meta_ads_provider


logger = get_logger(__name__)
META_REQUIRED_SCOPE = "ads_management"
META_OPTIMIZATION_GOAL = "OFFSITE_CONVERSIONS"
META_BILLING_EVENT = "IMPRESSIONS"
META_BID_STRATEGY = "LOWEST_COST_WITHOUT_CAP"


class MetaAdsAdSetPublishingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.connection_service = MetaAdsConnectionService(db)

    async def get_ad_set(
        self,
        campaign_id: UUID,
        publication_id: UUID,
        workspace_id: UUID,
    ) -> dict | None:
        await self._get_campaign(campaign_id, workspace_id)
        publication = await self._get_publication(
            campaign_id,
            publication_id,
            workspace_id,
            lock=False,
        )
        result = await self.db.execute(
            select(MetaAdsAdSetPublication).where(
                MetaAdsAdSetPublication.workspace_id == workspace_id,
                MetaAdsAdSetPublication.campaign_publication_id == publication.id,
            )
        )
        row = result.scalar_one_or_none()
        return self._serialize(row) if row is not None else None

    async def publish_paused_ad_set(
        self,
        campaign_id: UUID,
        publication_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        daily_budget_minor: int,
        target_country: str | None,
    ) -> dict:
        await self._require_admin_membership(workspace_id, user_id)
        campaign = await self._get_campaign(campaign_id, workspace_id)
        publication = await self._get_publication(
            campaign_id,
            publication_id,
            workspace_id,
            lock=True,
        )

        if publication.remote_status != "PAUSED":
            raise ForbiddenException("Meta campaign must remain PAUSED before creating an Ad Set")
        if not publication.pixel_id or not publication.page_id or not publication.delivery_configured_at:
            raise BadRequestException("Configure Meta delivery resources before creating an Ad Set")
        if daily_budget_minor <= 0:
            raise BadRequestException("Meta Ad Set daily budget must be greater than zero")

        country = (target_country or campaign.target_country or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", country):
            raise BadRequestException("Meta Ad Set target country must be a two-letter ISO code")

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
        currency = str(account.get("currency") or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise BadRequestException("Meta ad account currency is unavailable")

        await self._revalidate_delivery_resources(workspace_id, publication)

        existing_result = await self.db.execute(
            select(MetaAdsAdSetPublication).where(
                MetaAdsAdSetPublication.workspace_id == workspace_id,
                MetaAdsAdSetPublication.campaign_publication_id == publication.id,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            if (
                existing.daily_budget_minor != daily_budget_minor
                or existing.target_country != country
                or existing.currency != currency
            ):
                raise BadRequestException(
                    "A Meta Ad Set already exists for this publication with different immutable settings"
                )
            payload = self._serialize(existing)
            payload["reused"] = True
            return payload

        name = self._remote_ad_set_name(campaign, publication)
        provider = get_meta_ads_provider()
        try:
            remote = await provider.ensure_paused_ad_set(
                access_token,
                publication.ad_account_id,
                publication.remote_campaign_id,
                name,
                daily_budget_minor,
                country,
                publication.pixel_id,
            )
        except MetaAdsProviderError as exc:
            logger.warning("Meta Ads Ad Set creation failed: %s", type(exc).__name__)
            raise BadGatewayException("Meta Ads Ad Set creation failed") from exc

        remote_id = remote.get("id")
        if not isinstance(remote_id, str) or not remote_id:
            raise BadGatewayException("Meta Ads returned an invalid Ad Set response")
        remote_status = remote.get("status")
        if remote_status != "PAUSED":
            raise BadGatewayException("Meta Ads did not confirm the Ad Set as PAUSED")

        row = MetaAdsAdSetPublication(
            workspace_id=workspace_id,
            campaign_publication_id=publication.id,
            created_by_user_id=user_id,
            remote_ad_set_id=remote_id,
            remote_ad_set_name=name,
            remote_status="PAUSED",
            target_country=country,
            daily_budget_minor=daily_budget_minor,
            currency=currency,
            optimization_goal=META_OPTIMIZATION_GOAL,
            billing_event=META_BILLING_EVENT,
            bid_strategy=META_BID_STRATEGY,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        payload = self._serialize(row)
        payload["reused"] = bool(remote.get("reused"))
        return payload

    async def _revalidate_delivery_resources(
        self,
        workspace_id: UUID,
        publication: MetaAdsCampaignPublication,
    ) -> None:
        resources = await self.connection_service.get_delivery_resources(
            workspace_id,
            publication.ad_account_id,
        )
        pixel_ids = {item.get("id") for item in resources.get("pixels", []) if item.get("id")}
        page_ids = {item.get("id") for item in resources.get("pages", []) if item.get("id")}
        instagram_ids = {
            item.get("id") for item in resources.get("instagram_accounts", []) if item.get("id")
        }
        if publication.pixel_id not in pixel_ids:
            raise ForbiddenException("Configured Meta Pixel is no longer available to this ad account")
        if publication.page_id not in page_ids:
            raise ForbiddenException("Configured Facebook Page is no longer available to this ad account")
        if (
            publication.instagram_account_id is not None
            and publication.instagram_account_id not in instagram_ids
        ):
            raise ForbiddenException("Configured Instagram account is no longer available to this ad account")

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
        *,
        lock: bool,
    ) -> MetaAdsCampaignPublication:
        query = select(MetaAdsCampaignPublication).where(
            MetaAdsCampaignPublication.id == publication_id,
            MetaAdsCampaignPublication.campaign_id == campaign_id,
            MetaAdsCampaignPublication.workspace_id == workspace_id,
        )
        if lock:
            query = query.with_for_update()
        result = await self.db.execute(query)
        publication = result.scalar_one_or_none()
        if publication is None:
            raise NotFoundException("Meta Ads campaign publication")
        return publication

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
    def _remote_ad_set_name(
        campaign: Campaign,
        publication: MetaAdsCampaignPublication,
    ) -> str:
        marker = f"[VELNIO-ADSET:{publication.id}]"
        base = (campaign.name or "Velnio campaign").strip() or "Velnio campaign"
        max_base_length = max(1, 500 - len(marker) - 1)
        return f"{base[:max_base_length]} {marker}"

    @staticmethod
    def _serialize(row: MetaAdsAdSetPublication) -> dict:
        return {
            "id": str(row.id),
            "campaign_publication_id": str(row.campaign_publication_id),
            "remote_ad_set_id": row.remote_ad_set_id,
            "remote_ad_set_name": row.remote_ad_set_name,
            "remote_status": row.remote_status,
            "target_country": row.target_country,
            "daily_budget_minor": row.daily_budget_minor,
            "currency": row.currency,
            "optimization_goal": row.optimization_goal,
            "billing_event": row.billing_event,
            "bid_strategy": row.bid_strategy,
            "created_at": row.created_at,
        }
