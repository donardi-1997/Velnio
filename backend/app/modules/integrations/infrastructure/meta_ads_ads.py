from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.core.config import settings
from app.modules.integrations.infrastructure.meta_ads import (
    MetaAdsProviderError,
    MockMetaAdsProvider,
    RealMetaAdsProvider,
    UnsupportedMetaAdsProvider,
)


class MetaAdsAdProvider:
    async def ensure_paused_ad(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
        remote_ad_set_id: str,
        remote_creative_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError


class UnsupportedMetaAdsAdProvider(UnsupportedMetaAdsProvider, MetaAdsAdProvider):
    async def ensure_paused_ad(self, *args, **kwargs) -> dict[str, Any]:
        raise MetaAdsProviderError("Unsupported Meta Ads provider mode")


class MockMetaAdsAdProvider(MockMetaAdsProvider, MetaAdsAdProvider):
    async def ensure_paused_ad(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
        remote_ad_set_id: str,
        remote_creative_id: str,
    ) -> dict[str, Any]:
        self._validate_ad_account_id(ad_account_id)
        if not remote_ad_set_id or not remote_creative_id:
            raise MetaAdsProviderError("Invalid Meta Ad relationship")
        digest = hashlib.sha256(
            f"{ad_account_id}:{remote_ad_set_id}:{remote_creative_id}:{name}".encode("utf-8")
        ).hexdigest()[:20]
        return {
            "id": f"mock_meta_ad_{digest}",
            "name": name,
            "status": "PAUSED",
            "adset_id": remote_ad_set_id,
            "creative_id": remote_creative_id,
            "reused": False,
        }


class RealMetaAdsAdProvider(RealMetaAdsProvider, MetaAdsAdProvider):
    async def ensure_paused_ad(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
        remote_ad_set_id: str,
        remote_creative_id: str,
    ) -> dict[str, Any]:
        self._require_config()
        self._validate_ad_account_id(ad_account_id)
        self._validate_remote_id(remote_ad_set_id, "Ad Set")
        self._validate_remote_id(remote_creative_id, "AdCreative")

        existing = await self._find_ad_by_name(access_token, ad_account_id, name)
        if existing is not None:
            self._validate_existing_ad(
                existing,
                remote_ad_set_id=remote_ad_set_id,
                remote_creative_id=remote_creative_id,
            )
            return {
                "id": existing["id"],
                "name": name,
                "status": "PAUSED",
                "adset_id": remote_ad_set_id,
                "creative_id": remote_creative_id,
                "reused": True,
            }

        payload = await self._post_json(
            f"{self.graph_base}/{ad_account_id}/ads",
            data={
                "access_token": access_token,
                "name": name,
                "status": "PAUSED",
                "adset_id": remote_ad_set_id,
                "creative": json.dumps(
                    {"creative_id": remote_creative_id},
                    separators=(",", ":"),
                ),
            },
        )
        remote_id = payload.get("id")
        if not isinstance(remote_id, str) or not remote_id:
            raise MetaAdsProviderError("Meta returned an invalid Ad response")
        return {
            "id": remote_id,
            "name": name,
            "status": "PAUSED",
            "adset_id": remote_ad_set_id,
            "creative_id": remote_creative_id,
            "reused": False,
        }

    async def _find_ad_by_name(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
    ) -> dict[str, Any] | None:
        ads = await self._list_edge(
            f"{self.graph_base}/{ad_account_id}/ads",
            access_token,
            fields="id,name,status,effective_status,adset_id,creative{id}",
            max_pages=20,
        )
        for item in ads:
            if item.get("name") != name:
                continue
            remote_id = item.get("id")
            if not isinstance(remote_id, str) or not remote_id:
                raise MetaAdsProviderError("Meta returned an invalid Ad id")
            return item
        return None

    @staticmethod
    def _validate_existing_ad(
        item: dict[str, Any],
        *,
        remote_ad_set_id: str,
        remote_creative_id: str,
    ) -> None:
        if item.get("status") != "PAUSED":
            raise MetaAdsProviderError(
                "A matching Velnio Meta Ad exists but is not paused; refusing to adopt or modify it"
            )
        if str(item.get("adset_id") or "") != remote_ad_set_id:
            raise MetaAdsProviderError("Matching Meta Ad belongs to a different Ad Set")
        creative = item.get("creative") if isinstance(item.get("creative"), dict) else {}
        if str(creative.get("id") or "") != remote_creative_id:
            raise MetaAdsProviderError("Matching Meta Ad references a different AdCreative")

    @staticmethod
    def _validate_remote_id(value: str, resource: str) -> None:
        if not re.fullmatch(r"[0-9]+", value or ""):
            raise MetaAdsProviderError(f"Invalid Meta {resource} id")


def get_meta_ads_ad_provider() -> MetaAdsAdProvider:
    mode = settings.META_ADS_MODE.lower().strip()
    if mode == "mock":
        return MockMetaAdsAdProvider()
    if mode == "real":
        return RealMetaAdsAdProvider()
    return UnsupportedMetaAdsAdProvider()
