from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadGatewayException, BadRequestException, ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.models.campaign import Campaign, CampaignStatus
from app.models.meta_ads import (
    MetaAdsAdSetPublication,
    MetaAdsCampaignPublication,
    MetaAdsCreativePublication,
)
from app.models.product import ProductImage
from app.models.store import Store
from app.models.workspace import MemberRole, WorkspaceMember
from app.modules.integrations.application.meta_ads_connection import MetaAdsConnectionService
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError
from app.modules.integrations.infrastructure.meta_ads_creatives import (
    SUPPORTED_CTAS,
    get_meta_ads_creative_provider,
)


logger = get_logger(__name__)
META_REQUIRED_SCOPE = "ads_management"


class MetaAdsCreativePublishingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.connection_service = MetaAdsConnectionService(db)

    async def list_creatives(
        self,
        campaign_id: UUID,
        publication_id: UUID,
        workspace_id: UUID,
    ) -> list[dict]:
        await self._get_campaign(campaign_id, workspace_id)
        publication = await self._get_publication(campaign_id, publication_id, workspace_id)
        result = await self.db.execute(
            select(MetaAdsCreativePublication)
            .where(
                MetaAdsCreativePublication.workspace_id == workspace_id,
                MetaAdsCreativePublication.campaign_publication_id == publication.id,
            )
            .order_by(MetaAdsCreativePublication.created_at.desc())
        )
        return [self._serialize(row) for row in result.scalars().all()]

    async def publish_standalone_creative(
        self,
        campaign_id: UUID,
        publication_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        product_image_id: UUID,
        primary_text: str,
        headline: str | None,
        call_to_action: str,
    ) -> dict:
        await self._require_admin_membership(workspace_id, user_id)
        campaign = await self._get_campaign(campaign_id, workspace_id)
        publication = await self._get_publication(campaign_id, publication_id, workspace_id)
        ad_set = await self._get_ad_set(publication.id, workspace_id, lock=True)

        if publication.remote_status != "PAUSED":
            raise ForbiddenException("Meta campaign must remain PAUSED before creating a Creative")
        if ad_set.remote_status != "PAUSED":
            raise ForbiddenException("Meta Ad Set must remain PAUSED before creating a Creative")
        if campaign.status != CampaignStatus.PUBLISHED:
            raise BadRequestException("Publish the campaign to Shopify before creating a Meta Creative")
        if not publication.page_id or not publication.delivery_configured_at:
            raise BadRequestException("Configure Meta delivery resources before creating a Creative")

        destination_url = await self._validated_destination(campaign, workspace_id)
        image = await self._get_selected_image(campaign_id, product_image_id)
        image_url = self._require_public_https_url(image.image_url, "selected image")

        normalized_text = primary_text.strip()
        if not normalized_text:
            raise BadRequestException("Meta Creative primary text is required")
        normalized_headline = headline.strip() if headline and headline.strip() else None
        normalized_cta = call_to_action.strip().upper()
        if normalized_cta not in SUPPORTED_CTAS:
            raise BadRequestException("Unsupported Meta Creative call to action")

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

        await self._revalidate_delivery_resources(workspace_id, publication)

        idempotency_key = self._idempotency_key(
            ad_set.id,
            destination_url,
            image_url,
            normalized_text,
            normalized_headline,
            normalized_cta,
            publication.page_id,
            publication.instagram_account_id,
        )
        existing_result = await self.db.execute(
            select(MetaAdsCreativePublication).where(
                MetaAdsCreativePublication.workspace_id == workspace_id,
                MetaAdsCreativePublication.idempotency_key == idempotency_key,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            payload = self._serialize(existing)
            payload["reused"] = True
            return payload

        name = self._remote_creative_name(campaign, idempotency_key)
        provider = get_meta_ads_creative_provider()
        try:
            remote = await provider.ensure_standalone_creative(
                access_token,
                publication.ad_account_id,
                name,
                publication.page_id,
                publication.instagram_account_id,
                destination_url,
                image_url,
                normalized_text,
                normalized_headline,
                normalized_cta,
            )
        except MetaAdsProviderError as exc:
            logger.warning("Meta Ads Creative creation failed: %s", type(exc).__name__)
            raise BadGatewayException("Meta Ads Creative creation failed") from exc

        remote_id = remote.get("id")
        if not isinstance(remote_id, str) or not remote_id:
            raise BadGatewayException("Meta Ads returned an invalid Creative response")

        row = MetaAdsCreativePublication(
            workspace_id=workspace_id,
            campaign_publication_id=publication.id,
            ad_set_publication_id=ad_set.id,
            product_image_id=image.id,
            created_by_user_id=user_id,
            idempotency_key=idempotency_key,
            remote_creative_id=remote_id,
            remote_creative_name=name,
            destination_url=destination_url,
            image_url=image_url,
            primary_text=normalized_text,
            headline=normalized_headline,
            call_to_action=normalized_cta,
            page_id=publication.page_id,
            instagram_account_id=publication.instagram_account_id,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        payload = self._serialize(row)
        payload["reused"] = bool(remote.get("reused"))
        return payload

    async def _validated_destination(self, campaign: Campaign, workspace_id: UUID) -> str:
        if not campaign.store_id:
            raise BadRequestException("Campaign must belong to a Shopify store before creating a Meta Creative")
        result = await self.db.execute(
            select(Store).where(
                Store.id == campaign.store_id,
                Store.workspace_id == workspace_id,
            )
        )
        store = result.scalar_one_or_none()
        if store is None:
            raise NotFoundException("Store")
        if not store.shop_domain:
            raise BadRequestException("Shopify store domain is unavailable")

        destination = self._require_public_https_url(campaign.external_page_url or "", "Shopify landing")
        parsed = urlparse(destination)
        if parsed.hostname is None or parsed.hostname.lower() != store.shop_domain.strip().lower():
            raise BadRequestException("Stored Shopify landing URL does not belong to the campaign store")
        if not parsed.path.startswith("/pages/"):
            raise BadRequestException("Stored Shopify landing URL is not a published Velnio page")
        return destination

    async def _get_selected_image(self, campaign_id: UUID, image_id: UUID) -> ProductImage:
        result = await self.db.execute(
            select(ProductImage).where(
                ProductImage.id == image_id,
                ProductImage.campaign_id == campaign_id,
                ProductImage.selected.is_(True),
            )
        )
        image = result.scalar_one_or_none()
        if image is None:
            raise BadRequestException("Select this campaign image before creating a Meta Creative")
        return image

    async def _revalidate_delivery_resources(
        self,
        workspace_id: UUID,
        publication: MetaAdsCampaignPublication,
    ) -> None:
        resources = await self.connection_service.get_delivery_resources(
            workspace_id,
            publication.ad_account_id,
        )
        page_ids = {item.get("id") for item in resources.get("pages", []) if item.get("id")}
        instagram_ids = {
            item.get("id") for item in resources.get("instagram_accounts", []) if item.get("id")
        }
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
            raise BadRequestException("Create the paused Meta Ad Set before creating a Creative")
        return ad_set

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
    def _require_public_https_url(value: str, label: str) -> str:
        candidate = (value or "").strip()
        parsed = urlparse(candidate)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise BadRequestException(f"{label} URL must be a public HTTPS URL")
        return candidate

    @staticmethod
    def _idempotency_key(
        ad_set_publication_id: UUID,
        destination_url: str,
        image_url: str,
        primary_text: str,
        headline: str | None,
        call_to_action: str,
        page_id: str,
        instagram_account_id: str | None,
    ) -> str:
        canonical = {
            "ad_set_publication_id": str(ad_set_publication_id),
            "destination_url": destination_url,
            "image_url": image_url,
            "primary_text": primary_text,
            "headline": headline,
            "call_to_action": call_to_action,
            "page_id": page_id,
            "instagram_account_id": instagram_account_id,
        }
        raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _remote_creative_name(campaign: Campaign, idempotency_key: str) -> str:
        marker = f"[VELNIO-CREATIVE:{idempotency_key[:16]}]"
        base = (campaign.name or "Velnio campaign").strip() or "Velnio campaign"
        max_base_length = max(1, 500 - len(marker) - 1)
        return f"{base[:max_base_length]} {marker}"

    @staticmethod
    def _serialize(row: MetaAdsCreativePublication) -> dict:
        return {
            "id": str(row.id),
            "campaign_publication_id": str(row.campaign_publication_id),
            "ad_set_publication_id": str(row.ad_set_publication_id),
            "product_image_id": str(row.product_image_id) if row.product_image_id else None,
            "remote_creative_id": row.remote_creative_id,
            "remote_creative_name": row.remote_creative_name,
            "destination_url": row.destination_url,
            "image_url": row.image_url,
            "primary_text": row.primary_text,
            "headline": row.headline,
            "call_to_action": row.call_to_action,
            "page_id": row.page_id,
            "instagram_account_id": row.instagram_account_id,
            "created_at": row.created_at,
        }
