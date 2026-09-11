from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings
from app.modules.integrations.infrastructure.meta_ads import (
    MetaAdsProviderError,
    MockMetaAdsProvider,
    RealMetaAdsProvider,
    UnsupportedMetaAdsProvider,
)


SUPPORTED_CTAS = {"SHOP_NOW", "LEARN_MORE", "GET_OFFER"}


class MetaAdsCreativeProvider:
    async def ensure_standalone_creative(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
        page_id: str,
        instagram_account_id: str | None,
        destination_url: str,
        image_url: str,
        primary_text: str,
        headline: str | None,
        call_to_action: str,
    ) -> dict[str, Any]:
        raise NotImplementedError


class UnsupportedMetaAdsCreativeProvider(UnsupportedMetaAdsProvider, MetaAdsCreativeProvider):
    async def ensure_standalone_creative(self, *args, **kwargs) -> dict[str, Any]:
        raise MetaAdsProviderError("Unsupported Meta Ads provider mode")


class MockMetaAdsCreativeProvider(MockMetaAdsProvider, MetaAdsCreativeProvider):
    async def ensure_standalone_creative(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
        page_id: str,
        instagram_account_id: str | None,
        destination_url: str,
        image_url: str,
        primary_text: str,
        headline: str | None,
        call_to_action: str,
    ) -> dict[str, Any]:
        self._validate_ad_account_id(ad_account_id)
        _validate_creative_inputs(
            page_id,
            instagram_account_id,
            destination_url,
            image_url,
            primary_text,
            call_to_action,
        )
        digest = hashlib.sha256(f"{ad_account_id}:{name}".encode("utf-8")).hexdigest()[:20]
        return {
            "id": f"mock_meta_creative_{digest}",
            "name": name,
            "page_id": page_id,
            "instagram_account_id": instagram_account_id,
            "destination_url": destination_url,
            "image_url": image_url,
            "primary_text": primary_text,
            "headline": headline,
            "call_to_action": call_to_action,
            "reused": False,
        }


class RealMetaAdsCreativeProvider(RealMetaAdsProvider, MetaAdsCreativeProvider):
    async def ensure_standalone_creative(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
        page_id: str,
        instagram_account_id: str | None,
        destination_url: str,
        image_url: str,
        primary_text: str,
        headline: str | None,
        call_to_action: str,
    ) -> dict[str, Any]:
        self._require_config()
        self._validate_ad_account_id(ad_account_id)
        _validate_creative_inputs(
            page_id,
            instagram_account_id,
            destination_url,
            image_url,
            primary_text,
            call_to_action,
        )

        existing = await self._find_creative_by_name(access_token, ad_account_id, name)
        if existing is not None:
            self._validate_existing_creative(
                existing,
                page_id=page_id,
                instagram_account_id=instagram_account_id,
                destination_url=destination_url,
                image_url=image_url,
                primary_text=primary_text,
                headline=headline,
                call_to_action=call_to_action,
            )
            return {
                "id": existing["id"],
                "name": name,
                "page_id": page_id,
                "instagram_account_id": instagram_account_id,
                "destination_url": destination_url,
                "image_url": image_url,
                "primary_text": primary_text,
                "headline": headline,
                "call_to_action": call_to_action,
                "reused": True,
            }

        link_data: dict[str, Any] = {
            "call_to_action": {"type": call_to_action},
            "link": destination_url,
            "message": primary_text,
            "picture": image_url,
        }
        if headline:
            link_data["name"] = headline
        object_story_spec: dict[str, Any] = {
            "page_id": page_id,
            "link_data": link_data,
        }
        if instagram_account_id:
            object_story_spec["instagram_actor_id"] = instagram_account_id

        payload = await self._post_json(
            f"{self.graph_base}/{ad_account_id}/adcreatives",
            data={
                "access_token": access_token,
                "name": name,
                "object_story_spec": json.dumps(object_story_spec, separators=(",", ":")),
            },
        )
        remote_id = payload.get("id")
        if not isinstance(remote_id, str) or not remote_id:
            raise MetaAdsProviderError("Meta returned an invalid AdCreative response")
        return {
            "id": remote_id,
            "name": name,
            "page_id": page_id,
            "instagram_account_id": instagram_account_id,
            "destination_url": destination_url,
            "image_url": image_url,
            "primary_text": primary_text,
            "headline": headline,
            "call_to_action": call_to_action,
            "reused": False,
        }

    async def _find_creative_by_name(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
    ) -> dict[str, Any] | None:
        creatives = await self._list_edge(
            f"{self.graph_base}/{ad_account_id}/adcreatives",
            access_token,
            fields="id,name,object_story_spec",
            max_pages=20,
        )
        for item in creatives:
            if item.get("name") != name:
                continue
            remote_id = item.get("id")
            if not isinstance(remote_id, str) or not remote_id:
                raise MetaAdsProviderError("Meta returned an invalid AdCreative id")
            return item
        return None

    @staticmethod
    def _validate_existing_creative(
        item: dict[str, Any],
        *,
        page_id: str,
        instagram_account_id: str | None,
        destination_url: str,
        image_url: str,
        primary_text: str,
        headline: str | None,
        call_to_action: str,
    ) -> None:
        story = item.get("object_story_spec") if isinstance(item.get("object_story_spec"), dict) else {}
        if str(story.get("page_id") or "") != page_id:
            raise MetaAdsProviderError("Matching Meta AdCreative uses a different Facebook Page")
        existing_instagram = story.get("instagram_actor_id")
        if (str(existing_instagram) if existing_instagram else None) != instagram_account_id:
            raise MetaAdsProviderError("Matching Meta AdCreative uses a different Instagram account")

        link_data = story.get("link_data") if isinstance(story.get("link_data"), dict) else {}
        if str(link_data.get("link") or "") != destination_url:
            raise MetaAdsProviderError("Matching Meta AdCreative uses a different destination")
        if str(link_data.get("picture") or "") != image_url:
            raise MetaAdsProviderError("Matching Meta AdCreative uses a different image")
        if str(link_data.get("message") or "") != primary_text:
            raise MetaAdsProviderError("Matching Meta AdCreative uses different primary text")
        existing_headline = link_data.get("name")
        if (str(existing_headline) if existing_headline else None) != headline:
            raise MetaAdsProviderError("Matching Meta AdCreative uses a different headline")
        cta = link_data.get("call_to_action") if isinstance(link_data.get("call_to_action"), dict) else {}
        if str(cta.get("type") or "") != call_to_action:
            raise MetaAdsProviderError("Matching Meta AdCreative uses a different call to action")


def _validate_creative_inputs(
    page_id: str,
    instagram_account_id: str | None,
    destination_url: str,
    image_url: str,
    primary_text: str,
    call_to_action: str,
) -> None:
    if not re.fullmatch(r"[0-9]+", page_id):
        raise MetaAdsProviderError("Invalid Meta Page id")
    if instagram_account_id is not None and not re.fullmatch(r"[0-9]+", instagram_account_id):
        raise MetaAdsProviderError("Invalid Meta Instagram account id")
    if call_to_action not in SUPPORTED_CTAS:
        raise MetaAdsProviderError("Unsupported Meta call to action")
    if not primary_text.strip():
        raise MetaAdsProviderError("Meta AdCreative primary text is required")
    for value, label in ((destination_url, "destination"), (image_url, "image")):
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise MetaAdsProviderError(f"Meta AdCreative {label} URL must be a public HTTPS URL")


def get_meta_ads_creative_provider() -> MetaAdsCreativeProvider:
    mode = settings.META_ADS_MODE.lower().strip()
    if mode == "mock":
        return MockMetaAdsCreativeProvider()
    if mode == "real":
        return RealMetaAdsCreativeProvider()
    return UnsupportedMetaAdsCreativeProvider()
