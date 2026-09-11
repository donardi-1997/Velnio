from __future__ import annotations

from app.core.exceptions import BadGatewayException, ForbiddenException
from app.core.logging import get_logger
from app.models.meta_ads import MetaAdsAdSetPublication, MetaAdsCampaignPublication
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError
from app.modules.integrations.infrastructure.meta_ads_status import get_meta_ads_status_provider


logger = get_logger(__name__)


class MetaAdsRemoteStateGuard:
    async def require_paused_campaign(
        self,
        access_token: str,
        publication: MetaAdsCampaignPublication,
    ) -> dict:
        provider = get_meta_ads_status_provider()
        try:
            state = await provider.get_campaign_state(
                access_token,
                publication.ad_account_id,
                publication.remote_campaign_id,
            )
        except MetaAdsProviderError as exc:
            logger.warning("Meta Ads remote Campaign state verification failed: %s", type(exc).__name__)
            raise BadGatewayException("Could not verify current Meta Campaign state") from exc

        expected_account_id = publication.ad_account_id.removeprefix("act_")
        if state.get("id") != publication.remote_campaign_id:
            raise BadGatewayException("Meta returned an inconsistent Campaign state")
        if str(state.get("account_id") or "") != expected_account_id:
            raise ForbiddenException("Remote Meta Campaign no longer belongs to the configured ad account")
        if state.get("status") != "PAUSED":
            raise ForbiddenException("Remote Meta Campaign must be PAUSED before continuing")
        return state

    async def require_paused_hierarchy(
        self,
        access_token: str,
        publication: MetaAdsCampaignPublication,
        ad_set: MetaAdsAdSetPublication,
    ) -> dict:
        campaign_state = await self.require_paused_campaign(access_token, publication)
        provider = get_meta_ads_status_provider()
        try:
            ad_set_state = await provider.get_ad_set_state(
                access_token,
                publication.ad_account_id,
                publication.remote_campaign_id,
                ad_set.remote_ad_set_id,
            )
        except MetaAdsProviderError as exc:
            logger.warning("Meta Ads remote Ad Set state verification failed: %s", type(exc).__name__)
            raise BadGatewayException("Could not verify current Meta Ad Set state") from exc

        expected_account_id = publication.ad_account_id.removeprefix("act_")
        if ad_set_state.get("id") != ad_set.remote_ad_set_id:
            raise BadGatewayException("Meta returned an inconsistent Ad Set state")
        if str(ad_set_state.get("account_id") or "") != expected_account_id:
            raise ForbiddenException("Remote Meta Ad Set no longer belongs to the configured ad account")
        if ad_set_state.get("campaign_id") != publication.remote_campaign_id:
            raise ForbiddenException("Remote Meta Ad Set no longer belongs to the expected Campaign")
        if ad_set_state.get("status") != "PAUSED":
            raise ForbiddenException("Remote Meta Ad Set must be PAUSED before continuing")
        return {"campaign": campaign_state, "ad_set": ad_set_state}
