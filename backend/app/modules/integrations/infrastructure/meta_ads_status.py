from __future__ import annotations

import re
from typing import Any

from app.core.config import settings
from app.modules.integrations.infrastructure.meta_ads import (
    MetaAdsProviderError,
    MockMetaAdsProvider,
    RealMetaAdsProvider,
    UnsupportedMetaAdsProvider,
)


class MetaAdsStatusProvider:
    async def get_campaign_state(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def get_ad_set_state(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        remote_ad_set_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def get_ad_state(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        remote_ad_set_id: str,
        remote_creative_id: str,
        remote_ad_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError


class UnsupportedMetaAdsStatusProvider(UnsupportedMetaAdsProvider, MetaAdsStatusProvider):
    async def get_campaign_state(self, *args, **kwargs) -> dict[str, Any]:
        raise MetaAdsProviderError("Unsupported Meta Ads provider mode")

    async def get_ad_set_state(self, *args, **kwargs) -> dict[str, Any]:
        raise MetaAdsProviderError("Unsupported Meta Ads provider mode")

    async def get_ad_state(self, *args, **kwargs) -> dict[str, Any]:
        raise MetaAdsProviderError("Unsupported Meta Ads provider mode")


class MockMetaAdsStatusProvider(MockMetaAdsProvider, MetaAdsStatusProvider):
    async def get_campaign_state(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
    ) -> dict[str, Any]:
        self._validate_ad_account_id(ad_account_id)
        if not remote_campaign_id:
            raise MetaAdsProviderError("Invalid Meta Campaign id")
        return {
            "id": remote_campaign_id,
            "account_id": ad_account_id.removeprefix("act_"),
            "status": "PAUSED",
            "effective_status": "PAUSED",
        }

    async def get_ad_set_state(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        remote_ad_set_id: str,
    ) -> dict[str, Any]:
        self._validate_ad_account_id(ad_account_id)
        if not remote_campaign_id or not remote_ad_set_id:
            raise MetaAdsProviderError("Invalid Meta Ad Set hierarchy")
        return {
            "id": remote_ad_set_id,
            "account_id": ad_account_id.removeprefix("act_"),
            "campaign_id": remote_campaign_id,
            "status": "PAUSED",
            "effective_status": "PAUSED",
        }

    async def get_ad_state(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        remote_ad_set_id: str,
        remote_creative_id: str,
        remote_ad_id: str,
    ) -> dict[str, Any]:
        self._validate_ad_account_id(ad_account_id)
        if not all((remote_campaign_id, remote_ad_set_id, remote_creative_id, remote_ad_id)):
            raise MetaAdsProviderError("Invalid Meta Ad hierarchy")
        return {
            "id": remote_ad_id,
            "account_id": ad_account_id.removeprefix("act_"),
            "campaign_id": remote_campaign_id,
            "adset_id": remote_ad_set_id,
            "creative_id": remote_creative_id,
            "status": "PAUSED",
            "effective_status": "PAUSED",
        }


class RealMetaAdsStatusProvider(RealMetaAdsProvider, MetaAdsStatusProvider):
    async def get_campaign_state(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
    ) -> dict[str, Any]:
        self._require_config()
        self._validate_ad_account_id(ad_account_id)
        self._validate_remote_id(remote_campaign_id, "Campaign")
        payload = await self._get_json(
            self.graph_base,
            params={
                "ids": remote_campaign_id,
                "fields": "id,account_id,status,configured_status,effective_status",
                "access_token": access_token,
            },
        )
        item = payload.get(remote_campaign_id)
        if not isinstance(item, dict):
            raise MetaAdsProviderError("Meta returned an invalid Campaign state")
        return self._normalize_campaign_state(item, remote_campaign_id)

    async def get_ad_set_state(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        remote_ad_set_id: str,
    ) -> dict[str, Any]:
        self._require_config()
        self._validate_ad_account_id(ad_account_id)
        self._validate_remote_id(remote_campaign_id, "Campaign")
        self._validate_remote_id(remote_ad_set_id, "Ad Set")
        item = await self._get_json(
            f"{self.graph_base}/{remote_ad_set_id}",
            params={
                "fields": "id,account_id,campaign_id,status,effective_status",
                "access_token": access_token,
            },
        )
        return self._normalize_ad_set_state(item, remote_ad_set_id)

    async def get_ad_state(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        remote_ad_set_id: str,
        remote_creative_id: str,
        remote_ad_id: str,
    ) -> dict[str, Any]:
        self._require_config()
        self._validate_ad_account_id(ad_account_id)
        self._validate_remote_id(remote_campaign_id, "Campaign")
        self._validate_remote_id(remote_ad_set_id, "Ad Set")
        self._validate_remote_id(remote_creative_id, "AdCreative")
        self._validate_remote_id(remote_ad_id, "Ad")
        item = await self._get_json(
            f"{self.graph_base}/{remote_ad_id}",
            params={
                "fields": "id,account_id,campaign_id,adset_id,configured_status,status,effective_status,creative",
                "access_token": access_token,
            },
        )
        return self._normalize_ad_state(item, remote_ad_id)

    @staticmethod
    def _validate_remote_id(value: str, resource: str) -> None:
        if not re.fullmatch(r"[0-9]+", value or ""):
            raise MetaAdsProviderError(f"Invalid Meta {resource} id")

    @staticmethod
    def _normalize_campaign_state(item: dict[str, Any], expected_id: str) -> dict[str, Any]:
        remote_id = item.get("id")
        account_id = item.get("account_id")
        status = item.get("configured_status") or item.get("status")
        effective_status = item.get("effective_status")
        if str(remote_id or "") != expected_id:
            raise MetaAdsProviderError("Meta returned a mismatched Campaign state")
        if not isinstance(account_id, str) or not account_id:
            raise MetaAdsProviderError("Meta returned an invalid Campaign account")
        if not isinstance(status, str) or not status:
            raise MetaAdsProviderError("Meta returned an invalid Campaign status")
        return {
            "id": expected_id,
            "account_id": account_id,
            "status": status,
            "effective_status": effective_status if isinstance(effective_status, str) else None,
        }

    @staticmethod
    def _normalize_ad_set_state(item: dict[str, Any], expected_id: str) -> dict[str, Any]:
        remote_id = item.get("id")
        account_id = item.get("account_id")
        campaign_id = item.get("campaign_id")
        status = item.get("status")
        effective_status = item.get("effective_status")
        if str(remote_id or "") != expected_id:
            raise MetaAdsProviderError("Meta returned a mismatched Ad Set state")
        if not isinstance(account_id, str) or not account_id:
            raise MetaAdsProviderError("Meta returned an invalid Ad Set account")
        if not isinstance(campaign_id, str) or not campaign_id:
            raise MetaAdsProviderError("Meta returned an invalid Ad Set campaign")
        if not isinstance(status, str) or not status:
            raise MetaAdsProviderError("Meta returned an invalid Ad Set status")
        return {
            "id": expected_id,
            "account_id": account_id,
            "campaign_id": campaign_id,
            "status": status,
            "effective_status": effective_status if isinstance(effective_status, str) else None,
        }

    @staticmethod
    def _normalize_ad_state(item: dict[str, Any], expected_id: str) -> dict[str, Any]:
        remote_id = item.get("id")
        account_id = item.get("account_id")
        campaign_id = item.get("campaign_id")
        adset_id = item.get("adset_id")
        status = item.get("configured_status") or item.get("status")
        effective_status = item.get("effective_status")
        creative = item.get("creative") if isinstance(item.get("creative"), dict) else {}
        creative_id = creative.get("id")
        if str(remote_id or "") != expected_id:
            raise MetaAdsProviderError("Meta returned a mismatched Ad state")
        if not isinstance(account_id, str) or not account_id:
            raise MetaAdsProviderError("Meta returned an invalid Ad account")
        if not isinstance(campaign_id, str) or not campaign_id:
            raise MetaAdsProviderError("Meta returned an invalid Ad campaign")
        if not isinstance(adset_id, str) or not adset_id:
            raise MetaAdsProviderError("Meta returned an invalid Ad Set relationship")
        if not isinstance(creative_id, str) or not creative_id:
            raise MetaAdsProviderError("Meta returned an invalid AdCreative relationship")
        if not isinstance(status, str) or not status:
            raise MetaAdsProviderError("Meta returned an invalid Ad status")
        return {
            "id": expected_id,
            "account_id": account_id,
            "campaign_id": campaign_id,
            "adset_id": adset_id,
            "creative_id": creative_id,
            "status": status,
            "effective_status": effective_status if isinstance(effective_status, str) else None,
        }


def get_meta_ads_status_provider() -> MetaAdsStatusProvider:
    mode = settings.META_ADS_MODE.lower().strip()
    if mode == "mock":
        return MockMetaAdsStatusProvider()
    if mode == "real":
        return RealMetaAdsStatusProvider()
    return UnsupportedMetaAdsStatusProvider()
