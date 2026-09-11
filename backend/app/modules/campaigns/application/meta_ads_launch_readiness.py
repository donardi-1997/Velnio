from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundException
from app.models.campaign import Campaign, CampaignStatus
from app.models.meta_ads import (
    MetaAdsAdPublication,
    MetaAdsAdSetPublication,
    MetaAdsCampaignPublication,
    MetaAdsCreativePublication,
)
from app.models.store import Store, StoreStatus
from app.models.workspace import MemberRole, WorkspaceMember
from app.modules.campaigns.application.meta_ads_remote_state import MetaAdsRemoteStateGuard
from app.modules.integrations.application.meta_ads_connection import MetaAdsConnectionService


META_REQUIRED_SCOPE = "ads_management"


class MetaAdsLaunchReadinessService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.connection_service = MetaAdsConnectionService(db)
        self.remote_state_guard = MetaAdsRemoteStateGuard()

    async def get_readiness(
        self,
        campaign_id: UUID,
        publication_id: UUID,
        ad_publication_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> dict:
        campaign = await self._get_campaign(campaign_id, workspace_id)
        publication = await self._get_publication(campaign_id, publication_id, workspace_id)
        ad_set = await self._get_ad_set(publication.id, workspace_id)
        ad = await self._get_ad(ad_publication_id, publication.id, ad_set.id, workspace_id)
        creative = await self._get_creative(
            ad.creative_publication_id,
            publication.id,
            ad_set.id,
            workspace_id,
        )

        checks: list[dict] = []
        member = await self._get_membership(workspace_id, user_id)
        actor_allowed = member is not None and member.role in {MemberRole.OWNER, MemberRole.ADMIN}
        self._add_check(
            checks,
            "actor_role",
            actor_allowed,
            "Owner/admin authorization confirmed." if actor_allowed else "Only an owner or admin can launch Meta Ads.",
        )

        campaign_published = campaign.status == CampaignStatus.PUBLISHED and bool(campaign.external_page_url)
        self._add_check(
            checks,
            "shopify_published",
            campaign_published,
            "Campaign has a persisted Shopify landing URL."
            if campaign_published
            else "Publish the campaign to Shopify before launch.",
        )

        store = await self._get_store(campaign.store_id, workspace_id) if campaign.store_id else None
        store_connected = store is not None and store.status == StoreStatus.CONNECTED
        self._add_check(
            checks,
            "shopify_store_connection",
            store_connected,
            "Campaign Shopify store is connected to Velnio."
            if store_connected
            else "Reconnect the campaign Shopify store before launch.",
        )

        destination_ok = self._destination_matches_store(campaign.external_page_url, store)
        self._add_check(
            checks,
            "shopify_destination",
            destination_ok,
            "Shopify landing URL belongs to the campaign store."
            if destination_ok
            else "The persisted Shopify landing URL is missing or does not belong to the campaign store.",
        )

        creative_destination_ok = bool(
            campaign.external_page_url
            and creative.destination_url
            and campaign.external_page_url.strip() == creative.destination_url.strip()
        )
        self._add_check(
            checks,
            "creative_destination",
            creative_destination_ok,
            "Creative points to the currently published Shopify landing."
            if creative_destination_ok
            else "The Creative destination differs from the campaign's current Shopify landing; create a new Creative before launch.",
        )

        local_paused = publication.remote_status == "PAUSED" and ad_set.remote_status == "PAUSED" and ad.remote_status == "PAUSED"
        self._add_check(
            checks,
            "local_status_snapshots",
            local_paused,
            "Local Campaign, Ad Set and Ad snapshots are PAUSED."
            if local_paused
            else "A local Meta status snapshot is not PAUSED; refresh/reconcile before launch.",
        )

        delivery_configured = bool(
            publication.pixel_id
            and publication.page_id
            and publication.delivery_configured_at
        )
        self._add_check(
            checks,
            "delivery_config",
            delivery_configured,
            "Pixel and Facebook Page delivery configuration is present."
            if delivery_configured
            else "Configure a Meta Pixel and Facebook Page before launch.",
        )

        budget_ok = isinstance(ad_set.daily_budget_minor, int) and ad_set.daily_budget_minor > 0
        currency_ok = bool(re.fullmatch(r"[A-Z]{3}", (ad_set.currency or "").strip().upper()))
        country_ok = bool(re.fullmatch(r"[A-Z]{2}", (ad_set.target_country or "").strip().upper()))
        self._add_check(
            checks,
            "ad_set_budget",
            budget_ok,
            f"Daily budget is {ad_set.daily_budget_minor} {ad_set.currency} minor units."
            if budget_ok
            else "Meta Ad Set daily budget is invalid.",
        )
        self._add_check(
            checks,
            "ad_set_currency_country",
            currency_ok and country_ok,
            f"Ad Set currency/country are {ad_set.currency}/{ad_set.target_country}."
            if currency_ok and country_ok
            else "Meta Ad Set currency or target country is invalid.",
        )

        connection = await self.connection_service.get_active_connection(workspace_id)
        connection_ok = connection is not None
        self._add_check(
            checks,
            "meta_connection",
            connection_ok,
            "Meta Ads connection is active." if connection_ok else "Connect Meta Ads before launch.",
        )

        management_scope_ok = False
        access_token: str | None = None
        account: dict | None = None
        if connection is not None:
            granted = {part for part in re.split(r"[\s,]+", connection.scopes or "") if part}
            management_scope_ok = META_REQUIRED_SCOPE in granted
            try:
                access_token = await self.connection_service.get_valid_token(workspace_id)
            except AppException:
                access_token = None
        self._add_check(
            checks,
            "ads_management_scope",
            management_scope_ok,
            "Meta connection grants ads_management."
            if management_scope_ok
            else "Reconnect Meta Ads with ads_management before launch.",
        )
        self._add_check(
            checks,
            "meta_token",
            access_token is not None,
            "Meta access token is valid." if access_token is not None else "Meta access token is missing or expired; reconnect Meta Ads.",
        )

        if access_token is not None:
            try:
                accounts = await self.connection_service.list_ad_accounts(workspace_id)
                account = next((item for item in accounts if item.get("id") == publication.ad_account_id), None)
            except AppException:
                account = None
        account_ok = account is not None and account.get("account_status") in {None, 1}
        self._add_check(
            checks,
            "ad_account_access",
            account_ok,
            "Configured Meta ad account is accessible and active."
            if account_ok
            else "Configured Meta ad account is unavailable or inactive.",
        )

        account_currency = str(account.get("currency") or "").strip().upper() if account else ""
        account_currency_ok = account_ok and account_currency == ad_set.currency
        self._add_check(
            checks,
            "ad_account_currency",
            account_currency_ok,
            f"Ad account currency matches immutable Ad Set currency ({ad_set.currency})."
            if account_currency_ok
            else "Ad account currency no longer matches the Ad Set currency snapshot.",
        )

        delivery_resources_ok = False
        if account_ok and delivery_configured:
            try:
                resources = await self.connection_service.get_delivery_resources(
                    workspace_id,
                    publication.ad_account_id,
                )
                pixel_ids = {item.get("id") for item in resources.get("pixels", []) if item.get("id")}
                page_ids = {item.get("id") for item in resources.get("pages", []) if item.get("id")}
                instagram_ids = {
                    item.get("id")
                    for item in resources.get("instagram_accounts", [])
                    if item.get("id")
                }
                delivery_resources_ok = (
                    publication.pixel_id in pixel_ids
                    and publication.page_id in page_ids
                    and (
                        publication.instagram_account_id is None
                        or publication.instagram_account_id in instagram_ids
                    )
                )
            except AppException:
                delivery_resources_ok = False
        self._add_check(
            checks,
            "delivery_resources_live",
            delivery_resources_ok,
            "Configured Pixel/Page/Instagram resources are still available to the ad account."
            if delivery_resources_ok
            else "One or more configured Meta delivery resources are no longer available.",
        )

        remote_hierarchy_ok = False
        remote_states: dict | None = None
        remote_message = "Live Meta hierarchy could not be verified."
        if access_token is not None and account_ok:
            try:
                remote_states = await self.remote_state_guard.require_paused_full_hierarchy(
                    access_token,
                    publication,
                    ad_set,
                    creative,
                    ad,
                )
                remote_hierarchy_ok = True
                remote_message = "Live Meta Campaign, Ad Set and Ad are related correctly and configured PAUSED."
            except AppException as exc:
                remote_message = str(exc.detail)
        self._add_check(
            checks,
            "remote_paused_hierarchy",
            remote_hierarchy_ok,
            remote_message,
        )

        ready = all(item["status"] == "PASS" for item in checks)
        launch_plan = {
            "ad_account_id": publication.ad_account_id,
            "remote_campaign_id": publication.remote_campaign_id,
            "remote_ad_set_id": ad_set.remote_ad_set_id,
            "remote_ad_id": ad.remote_ad_id,
            "remote_creative_id": creative.remote_creative_id,
            "destination_url": creative.destination_url,
            "pixel_id": publication.pixel_id,
            "page_id": publication.page_id,
            "instagram_account_id": publication.instagram_account_id,
            "daily_budget_minor": ad_set.daily_budget_minor,
            "currency": ad_set.currency,
            "target_country": ad_set.target_country,
            "current_configured_statuses": {
                "campaign": remote_states["campaign"]["status"] if remote_states else None,
                "ad_set": remote_states["ad_set"]["status"] if remote_states else None,
                "ad": remote_states["ad"]["status"] if remote_states else None,
            },
            "proposed_statuses": {
                "campaign": "ACTIVE",
                "ad_set": "ACTIVE",
                "ad": "ACTIVE",
            },
        }
        payload = {
            "ready": ready,
            "side_effects_performed": False,
            "checks": checks,
            "launch_plan": launch_plan,
        }
        payload["readiness_fingerprint"] = self.fingerprint(payload)
        return payload

    @staticmethod
    def fingerprint(readiness: dict) -> str:
        canonical = {
            "checks": [
                {"key": item.get("key"), "status": item.get("status")}
                for item in readiness.get("checks", [])
            ],
            "launch_plan": readiness.get("launch_plan", {}),
        }
        encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    async def _get_campaign(self, campaign_id: UUID, workspace_id: UUID) -> Campaign:
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == workspace_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundException("Campaign")
        return row

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
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundException("Meta Ads campaign publication")
        return row

    async def _get_ad_set(self, publication_id: UUID, workspace_id: UUID) -> MetaAdsAdSetPublication:
        result = await self.db.execute(
            select(MetaAdsAdSetPublication).where(
                MetaAdsAdSetPublication.workspace_id == workspace_id,
                MetaAdsAdSetPublication.campaign_publication_id == publication_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundException("Meta Ads Ad Set publication")
        return row

    async def _get_ad(
        self,
        ad_id: UUID,
        publication_id: UUID,
        ad_set_id: UUID,
        workspace_id: UUID,
    ) -> MetaAdsAdPublication:
        result = await self.db.execute(
            select(MetaAdsAdPublication).where(
                MetaAdsAdPublication.id == ad_id,
                MetaAdsAdPublication.workspace_id == workspace_id,
                MetaAdsAdPublication.campaign_publication_id == publication_id,
                MetaAdsAdPublication.ad_set_publication_id == ad_set_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundException("Meta Ads Ad publication")
        return row

    async def _get_creative(
        self,
        creative_id: UUID,
        publication_id: UUID,
        ad_set_id: UUID,
        workspace_id: UUID,
    ) -> MetaAdsCreativePublication:
        result = await self.db.execute(
            select(MetaAdsCreativePublication).where(
                MetaAdsCreativePublication.id == creative_id,
                MetaAdsCreativePublication.workspace_id == workspace_id,
                MetaAdsCreativePublication.campaign_publication_id == publication_id,
                MetaAdsCreativePublication.ad_set_publication_id == ad_set_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundException("Meta Ads Creative publication")
        return row

    async def _get_membership(self, workspace_id: UUID, user_id: UUID) -> WorkspaceMember | None:
        result = await self.db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_store(self, store_id: UUID, workspace_id: UUID) -> Store | None:
        result = await self.db.execute(
            select(Store).where(Store.id == store_id, Store.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _destination_matches_store(destination: str | None, store: Store | None) -> bool:
        if not destination or store is None or not store.shop_domain:
            return False
        parsed = urlparse(destination.strip())
        return bool(
            parsed.scheme == "https"
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
            and parsed.hostname.lower() == store.shop_domain.strip().lower()
            and parsed.path.startswith("/pages/")
        )

    @staticmethod
    def _add_check(checks: list[dict], key: str, passed: bool, message: str) -> None:
        checks.append({"key": key, "status": "PASS" if passed else "FAIL", "message": message})
