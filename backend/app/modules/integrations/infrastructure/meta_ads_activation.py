from __future__ import annotations

import re
from typing import Any, Awaitable, Callable

from app.core.config import settings
from app.modules.integrations.infrastructure.meta_ads import (
    MetaAdsProviderError,
    MockMetaAdsProvider,
    RealMetaAdsProvider,
    UnsupportedMetaAdsProvider,
)
from app.modules.integrations.infrastructure.meta_ads_status import RealMetaAdsStatusProvider


_ALLOWED_STATUSES = {"PAUSED", "ACTIVE"}


class MetaAdsActivationProvider:
    async def set_ad_status(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        remote_ad_set_id: str,
        remote_creative_id: str,
        remote_ad_id: str,
        target_status: str,
        *,
        expected_status: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def set_ad_set_status(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        remote_ad_set_id: str,
        target_status: str,
        *,
        expected_status: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def set_campaign_status(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        target_status: str,
        *,
        expected_status: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class UnsupportedMetaAdsActivationProvider(UnsupportedMetaAdsProvider, MetaAdsActivationProvider):
    async def set_ad_status(self, *args, **kwargs) -> dict[str, Any]:
        raise MetaAdsProviderError("Unsupported Meta Ads provider mode")

    async def set_ad_set_status(self, *args, **kwargs) -> dict[str, Any]:
        raise MetaAdsProviderError("Unsupported Meta Ads provider mode")

    async def set_campaign_status(self, *args, **kwargs) -> dict[str, Any]:
        raise MetaAdsProviderError("Unsupported Meta Ads provider mode")


class MockMetaAdsActivationProvider(MockMetaAdsProvider, MetaAdsActivationProvider):
    async def set_ad_status(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        remote_ad_set_id: str,
        remote_creative_id: str,
        remote_ad_id: str,
        target_status: str,
        *,
        expected_status: str | None = None,
    ) -> dict[str, Any]:
        self._validate_ad_account_id(ad_account_id)
        self._validate_status(target_status)
        if not all((remote_campaign_id, remote_ad_set_id, remote_creative_id, remote_ad_id)):
            raise MetaAdsProviderError("Invalid Meta Ad hierarchy")
        return {
            "id": remote_ad_id,
            "account_id": ad_account_id.removeprefix("act_"),
            "campaign_id": remote_campaign_id,
            "adset_id": remote_ad_set_id,
            "creative_id": remote_creative_id,
            "status": target_status,
            "effective_status": target_status,
        }

    async def set_ad_set_status(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        remote_ad_set_id: str,
        target_status: str,
        *,
        expected_status: str | None = None,
    ) -> dict[str, Any]:
        self._validate_ad_account_id(ad_account_id)
        self._validate_status(target_status)
        if not remote_campaign_id or not remote_ad_set_id:
            raise MetaAdsProviderError("Invalid Meta Ad Set hierarchy")
        return {
            "id": remote_ad_set_id,
            "account_id": ad_account_id.removeprefix("act_"),
            "campaign_id": remote_campaign_id,
            "status": target_status,
            "effective_status": target_status,
        }

    async def set_campaign_status(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        target_status: str,
        *,
        expected_status: str | None = None,
    ) -> dict[str, Any]:
        self._validate_ad_account_id(ad_account_id)
        self._validate_status(target_status)
        if not remote_campaign_id:
            raise MetaAdsProviderError("Invalid Meta Campaign id")
        return {
            "id": remote_campaign_id,
            "account_id": ad_account_id.removeprefix("act_"),
            "status": target_status,
            "effective_status": target_status,
        }

    @staticmethod
    def _validate_status(status: str) -> None:
        if status not in _ALLOWED_STATUSES:
            raise MetaAdsProviderError("Unsupported Meta status transition")


class RealMetaAdsActivationProvider(RealMetaAdsProvider, MetaAdsActivationProvider):
    def __init__(self) -> None:
        super().__init__()
        self.status_provider = RealMetaAdsStatusProvider()

    async def set_ad_status(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        remote_ad_set_id: str,
        remote_creative_id: str,
        remote_ad_id: str,
        target_status: str,
        *,
        expected_status: str | None = None,
    ) -> dict[str, Any]:
        self._validate_transition_inputs(ad_account_id, target_status, expected_status)
        self._validate_remote_id(remote_campaign_id, "Campaign")
        self._validate_remote_id(remote_ad_set_id, "Ad Set")
        self._validate_remote_id(remote_creative_id, "AdCreative")
        self._validate_remote_id(remote_ad_id, "Ad")

        async def get_state() -> dict[str, Any]:
            state = await self.status_provider.get_ad_state(
                access_token,
                ad_account_id,
                remote_campaign_id,
                remote_ad_set_id,
                remote_creative_id,
                remote_ad_id,
            )
            self._validate_ad_relationships(
                state,
                ad_account_id,
                remote_campaign_id,
                remote_ad_set_id,
                remote_creative_id,
                remote_ad_id,
            )
            return state

        return await self._transition(
            access_token,
            remote_ad_id,
            target_status,
            expected_status,
            get_state,
        )

    async def set_ad_set_status(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        remote_ad_set_id: str,
        target_status: str,
        *,
        expected_status: str | None = None,
    ) -> dict[str, Any]:
        self._validate_transition_inputs(ad_account_id, target_status, expected_status)
        self._validate_remote_id(remote_campaign_id, "Campaign")
        self._validate_remote_id(remote_ad_set_id, "Ad Set")

        async def get_state() -> dict[str, Any]:
            state = await self.status_provider.get_ad_set_state(
                access_token,
                ad_account_id,
                remote_campaign_id,
                remote_ad_set_id,
            )
            self._validate_ad_set_relationships(
                state,
                ad_account_id,
                remote_campaign_id,
                remote_ad_set_id,
            )
            return state

        return await self._transition(
            access_token,
            remote_ad_set_id,
            target_status,
            expected_status,
            get_state,
        )

    async def set_campaign_status(
        self,
        access_token: str,
        ad_account_id: str,
        remote_campaign_id: str,
        target_status: str,
        *,
        expected_status: str | None = None,
    ) -> dict[str, Any]:
        self._validate_transition_inputs(ad_account_id, target_status, expected_status)
        self._validate_remote_id(remote_campaign_id, "Campaign")

        async def get_state() -> dict[str, Any]:
            state = await self.status_provider.get_campaign_state(
                access_token,
                ad_account_id,
                remote_campaign_id,
            )
            self._validate_campaign_relationships(state, ad_account_id, remote_campaign_id)
            return state

        return await self._transition(
            access_token,
            remote_campaign_id,
            target_status,
            expected_status,
            get_state,
        )

    async def _transition(
        self,
        access_token: str,
        remote_id: str,
        target_status: str,
        expected_status: str | None,
        get_state: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        before = await get_state()
        current_status = before.get("status")
        if current_status == target_status:
            if target_status == "PAUSED":
                return before
            raise MetaAdsProviderError(
                "Meta resource is already ACTIVE outside the expected Velnio launch transition"
            )
        if expected_status is not None and current_status != expected_status:
            raise MetaAdsProviderError("Meta resource status changed before transition")

        payload = await self._post_json(
            f"{self.graph_base}/{remote_id}",
            data={"access_token": access_token, "status": target_status},
        )
        success = payload.get("success")
        if success is not None and success is not True:
            raise MetaAdsProviderError("Meta did not accept the status transition")

        after = await get_state()
        if after.get("status") != target_status:
            raise MetaAdsProviderError("Meta did not confirm the requested status transition")
        return after

    def _validate_transition_inputs(
        self,
        ad_account_id: str,
        target_status: str,
        expected_status: str | None,
    ) -> None:
        self._require_config()
        self._validate_ad_account_id(ad_account_id)
        if target_status not in _ALLOWED_STATUSES:
            raise MetaAdsProviderError("Unsupported Meta status transition")
        if expected_status is not None and expected_status not in _ALLOWED_STATUSES:
            raise MetaAdsProviderError("Unsupported expected Meta status")

    @staticmethod
    def _validate_remote_id(value: str, resource: str) -> None:
        if not re.fullmatch(r"[0-9]+", value or ""):
            raise MetaAdsProviderError(f"Invalid Meta {resource} id")

    @staticmethod
    def _expected_account_id(ad_account_id: str) -> str:
        return ad_account_id.removeprefix("act_")

    @classmethod
    def _validate_campaign_relationships(
        cls,
        state: dict[str, Any],
        ad_account_id: str,
        campaign_id: str,
    ) -> None:
        if state.get("id") != campaign_id:
            raise MetaAdsProviderError("Meta returned a mismatched Campaign")
        if str(state.get("account_id") or "") != cls._expected_account_id(ad_account_id):
            raise MetaAdsProviderError("Meta Campaign belongs to a different ad account")

    @classmethod
    def _validate_ad_set_relationships(
        cls,
        state: dict[str, Any],
        ad_account_id: str,
        campaign_id: str,
        ad_set_id: str,
    ) -> None:
        if state.get("id") != ad_set_id:
            raise MetaAdsProviderError("Meta returned a mismatched Ad Set")
        if str(state.get("account_id") or "") != cls._expected_account_id(ad_account_id):
            raise MetaAdsProviderError("Meta Ad Set belongs to a different ad account")
        if state.get("campaign_id") != campaign_id:
            raise MetaAdsProviderError("Meta Ad Set belongs to a different Campaign")

    @classmethod
    def _validate_ad_relationships(
        cls,
        state: dict[str, Any],
        ad_account_id: str,
        campaign_id: str,
        ad_set_id: str,
        creative_id: str,
        ad_id: str,
    ) -> None:
        if state.get("id") != ad_id:
            raise MetaAdsProviderError("Meta returned a mismatched Ad")
        if str(state.get("account_id") or "") != cls._expected_account_id(ad_account_id):
            raise MetaAdsProviderError("Meta Ad belongs to a different ad account")
        if state.get("campaign_id") != campaign_id:
            raise MetaAdsProviderError("Meta Ad belongs to a different Campaign")
        if state.get("adset_id") != ad_set_id:
            raise MetaAdsProviderError("Meta Ad belongs to a different Ad Set")
        if state.get("creative_id") != creative_id:
            raise MetaAdsProviderError("Meta Ad references a different AdCreative")


def get_meta_ads_activation_provider() -> MetaAdsActivationProvider:
    mode = settings.META_ADS_MODE.lower().strip()
    if mode == "mock":
        return MockMetaAdsActivationProvider()
    if mode == "real":
        return RealMetaAdsActivationProvider()
    return UnsupportedMetaAdsActivationProvider()
