from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib
import re
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger(__name__)


class MetaAdsProviderError(Exception):
    """Safe provider-boundary error; never include upstream response bodies."""


class MetaAdsProvider(ABC):
    @abstractmethod
    async def get_auth_url(self, state: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def exchange_code(self, code: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_profile(self, access_token: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def list_ad_accounts(self, access_token: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def ensure_paused_campaign(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
        objective: str,
    ) -> dict[str, Any]:
        raise NotImplementedError


class UnsupportedMetaAdsProvider(MetaAdsProvider):
    async def get_auth_url(self, state: str) -> str:
        raise MetaAdsProviderError("Unsupported Meta Ads provider mode")

    async def exchange_code(self, code: str) -> dict[str, Any]:
        raise MetaAdsProviderError("Unsupported Meta Ads provider mode")

    async def get_profile(self, access_token: str) -> dict[str, Any]:
        raise MetaAdsProviderError("Unsupported Meta Ads provider mode")

    async def list_ad_accounts(self, access_token: str) -> list[dict[str, Any]]:
        raise MetaAdsProviderError("Unsupported Meta Ads provider mode")

    async def ensure_paused_campaign(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
        objective: str,
    ) -> dict[str, Any]:
        raise MetaAdsProviderError("Unsupported Meta Ads provider mode")


class MockMetaAdsProvider(MetaAdsProvider):
    async def get_auth_url(self, state: str) -> str:
        return f"mock://meta-ads/oauth?state={state}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        return {
            "access_token": "mock_meta_access_token",
            "expires_in": 60 * 60 * 24 * 60,
            "scope": settings.META_ADS_SCOPES,
        }

    async def get_profile(self, access_token: str) -> dict[str, Any]:
        return {"id": "100000000000001", "name": "Velnio Meta Demo"}

    async def list_ad_accounts(self, access_token: str) -> list[dict[str, Any]]:
        return [
            {
                "id": "act_1000000001",
                "account_id": "1000000001",
                "name": "Velnio Demo Ads",
                "account_status": 1,
                "currency": "USD",
                "timezone_name": "America/Bogota",
            },
            {
                "id": "act_1000000002",
                "account_id": "1000000002",
                "name": "Velnio Test Ads",
                "account_status": 1,
                "currency": "COP",
                "timezone_name": "America/Bogota",
            },
        ]

    async def ensure_paused_campaign(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
        objective: str,
    ) -> dict[str, Any]:
        self._validate_ad_account_id(ad_account_id)
        digest = hashlib.sha256(f"{ad_account_id}:{name}".encode("utf-8")).hexdigest()[:20]
        return {
            "id": f"mock_meta_campaign_{digest}",
            "name": name,
            "status": "PAUSED",
            "objective": objective,
            "reused": False,
        }

    @staticmethod
    def _validate_ad_account_id(ad_account_id: str) -> None:
        if not re.fullmatch(r"act_[0-9]+", ad_account_id):
            raise MetaAdsProviderError("Invalid Meta ad account id")


class RealMetaAdsProvider(MetaAdsProvider):
    def __init__(self) -> None:
        self.graph_base = f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}"

    def _require_config(self) -> None:
        if not settings.META_APP_ID or not settings.META_APP_SECRET:
            raise MetaAdsProviderError("Meta Ads integration is not configured")
        if not settings.META_REDIRECT_URI.startswith(("https://", "http://localhost")):
            raise MetaAdsProviderError("Meta Ads redirect URI is not configured safely")

    async def get_auth_url(self, state: str) -> str:
        self._require_config()
        params = {
            "client_id": settings.META_APP_ID,
            "redirect_uri": settings.META_REDIRECT_URI,
            "state": state,
            "scope": settings.META_ADS_SCOPES,
            "response_type": "code",
        }
        return (
            f"https://www.facebook.com/{settings.META_GRAPH_API_VERSION}/dialog/oauth?"
            f"{urlencode(params)}"
        )

    async def exchange_code(self, code: str) -> dict[str, Any]:
        self._require_config()
        short_lived = await self._get_json(
            f"{self.graph_base}/oauth/access_token",
            params={
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "redirect_uri": settings.META_REDIRECT_URI,
                "code": code,
            },
        )
        short_token = self._require_token(short_lived)

        long_lived = await self._get_json(
            f"{self.graph_base}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "fb_exchange_token": short_token,
            },
        )
        access_token = self._require_token(long_lived)
        expires_in = self._parse_expires_in(long_lived)
        return {
            "access_token": access_token,
            "expires_in": expires_in,
            "scope": settings.META_ADS_SCOPES,
        }

    async def get_profile(self, access_token: str) -> dict[str, Any]:
        data = await self._get_json(
            f"{self.graph_base}/me",
            params={"fields": "id,name", "access_token": access_token},
        )
        user_id = data.get("id")
        if not isinstance(user_id, str) or not user_id:
            raise MetaAdsProviderError("Meta returned an invalid user profile")
        name = data.get("name")
        return {
            "id": user_id,
            "name": name if isinstance(name, str) and name else None,
        }

    async def list_ad_accounts(self, access_token: str) -> list[dict[str, Any]]:
        accounts: list[dict[str, Any]] = []
        after: str | None = None
        for _ in range(10):
            params: dict[str, Any] = {
                "fields": "id,account_id,name,account_status,currency,timezone_name",
                "limit": 100,
                "access_token": access_token,
            }
            if after:
                params["after"] = after
            payload = await self._get_json(f"{self.graph_base}/me/adaccounts", params=params)
            data = payload.get("data")
            if not isinstance(data, list):
                raise MetaAdsProviderError("Meta returned an invalid ad account response")
            for item in data:
                if not isinstance(item, dict):
                    continue
                account_id = item.get("id")
                if not isinstance(account_id, str) or not account_id.startswith("act_"):
                    continue
                accounts.append(
                    {
                        "id": account_id,
                        "account_id": str(item.get("account_id") or account_id.removeprefix("act_")),
                        "name": str(item.get("name") or "Unnamed ad account"),
                        "account_status": item.get("account_status"),
                        "currency": item.get("currency"),
                        "timezone_name": item.get("timezone_name"),
                    }
                )
            after = self._next_cursor(payload, after)
            if after is None:
                break
        return accounts

    async def ensure_paused_campaign(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
        objective: str,
    ) -> dict[str, Any]:
        self._require_config()
        self._validate_ad_account_id(ad_account_id)
        existing = await self._find_campaign_by_name(access_token, ad_account_id, name)
        if existing is not None:
            status = existing.get("status")
            if status != "PAUSED":
                raise MetaAdsProviderError(
                    "A matching Velnio Meta campaign exists but is not paused; refusing to adopt or modify it"
                )
            return {
                "id": existing["id"],
                "name": name,
                "status": "PAUSED",
                "objective": objective,
                "reused": True,
            }

        payload = await self._post_json(
            f"{self.graph_base}/{ad_account_id}/campaigns",
            data={
                "access_token": access_token,
                "name": name,
                "objective": objective,
                "status": "PAUSED",
                "buying_type": "AUCTION",
                "special_ad_categories": "[]",
            },
        )
        remote_id = payload.get("id")
        if not isinstance(remote_id, str) or not remote_id:
            raise MetaAdsProviderError("Meta returned an invalid campaign response")
        return {
            "id": remote_id,
            "name": name,
            "status": "PAUSED",
            "objective": objective,
            "reused": False,
        }

    async def _find_campaign_by_name(
        self,
        access_token: str,
        ad_account_id: str,
        name: str,
    ) -> dict[str, Any] | None:
        after: str | None = None
        for _ in range(20):
            params: dict[str, Any] = {
                "fields": "id,name,status,effective_status",
                "limit": 100,
                "access_token": access_token,
            }
            if after:
                params["after"] = after
            payload = await self._get_json(
                f"{self.graph_base}/{ad_account_id}/campaigns",
                params=params,
            )
            data = payload.get("data")
            if not isinstance(data, list):
                raise MetaAdsProviderError("Meta returned an invalid campaign list response")
            for item in data:
                if not isinstance(item, dict) or item.get("name") != name:
                    continue
                remote_id = item.get("id")
                if not isinstance(remote_id, str) or not remote_id:
                    raise MetaAdsProviderError("Meta returned an invalid campaign id")
                return item
            after = self._next_cursor(payload, after)
            if after is None:
                break
        return None

    @staticmethod
    def _next_cursor(payload: dict[str, Any], previous: str | None) -> str | None:
        paging = payload.get("paging") if isinstance(payload.get("paging"), dict) else {}
        cursors = paging.get("cursors") if isinstance(paging.get("cursors"), dict) else {}
        value = cursors.get("after")
        if not isinstance(value, str) or not value or value == previous:
            return None
        return value

    async def _get_json(self, url: str, *, params: dict[str, Any]) -> dict[str, Any]:
        try:
            timeout = httpx.Timeout(settings.META_REQUEST_TIMEOUT_SECONDS)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            logger.warning("Meta Ads request timed out")
            raise MetaAdsProviderError("Meta Ads request timed out") from exc
        except httpx.RequestError as exc:
            logger.warning("Meta Ads network request failed: %s", type(exc).__name__)
            raise MetaAdsProviderError("Meta Ads is temporarily unavailable") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning("Meta Ads returned HTTP %s", exc.response.status_code)
            raise MetaAdsProviderError("Meta Ads rejected the request") from exc
        except ValueError as exc:
            logger.warning("Meta Ads returned invalid JSON")
            raise MetaAdsProviderError("Meta Ads returned an invalid response") from exc

        if not isinstance(payload, dict) or payload.get("error"):
            raise MetaAdsProviderError("Meta Ads returned an invalid response")
        return payload

    async def _post_json(self, url: str, *, data: dict[str, Any]) -> dict[str, Any]:
        try:
            timeout = httpx.Timeout(settings.META_REQUEST_TIMEOUT_SECONDS)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, data=data)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            logger.warning("Meta Ads campaign request timed out")
            raise MetaAdsProviderError("Meta Ads request timed out") from exc
        except httpx.RequestError as exc:
            logger.warning("Meta Ads campaign network request failed: %s", type(exc).__name__)
            raise MetaAdsProviderError("Meta Ads is temporarily unavailable") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning("Meta Ads campaign request returned HTTP %s", exc.response.status_code)
            raise MetaAdsProviderError("Meta Ads rejected the campaign request") from exc
        except ValueError as exc:
            logger.warning("Meta Ads campaign request returned invalid JSON")
            raise MetaAdsProviderError("Meta Ads returned an invalid response") from exc

        if not isinstance(payload, dict) or payload.get("error"):
            raise MetaAdsProviderError("Meta Ads returned an invalid response")
        return payload

    @staticmethod
    def _validate_ad_account_id(ad_account_id: str) -> None:
        if not re.fullmatch(r"act_[0-9]+", ad_account_id):
            raise MetaAdsProviderError("Invalid Meta ad account id")

    @staticmethod
    def _require_token(payload: dict[str, Any]) -> str:
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise MetaAdsProviderError("Meta did not return an access token")
        return token

    @staticmethod
    def _parse_expires_in(payload: dict[str, Any]) -> int:
        try:
            expires_in = int(payload.get("expires_in", 0))
        except (TypeError, ValueError) as exc:
            raise MetaAdsProviderError("Meta returned an invalid token expiry") from exc
        if expires_in <= 0:
            raise MetaAdsProviderError("Meta returned an invalid token expiry")
        return expires_in


def get_meta_ads_provider() -> MetaAdsProvider:
    mode = settings.META_ADS_MODE.lower().strip()
    if mode == "mock":
        return MockMetaAdsProvider()
    if mode == "real":
        return RealMetaAdsProvider()
    return UnsupportedMetaAdsProvider()
