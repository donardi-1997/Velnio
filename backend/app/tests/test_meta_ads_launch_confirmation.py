from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.meta_ads import (
    MetaAdsAdPublication,
    MetaAdsAdSetPublication,
    MetaAdsCampaignPublication,
    MetaAdsLaunchIntent,
)
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError
from app.tests.test_meta_ads_launch_readiness import (
    _headers,
    _intent_path,
    _path,
    _register,
    _setup_ready,
)


def _confirm_path(campaign_id: str, publication_id: str, ad_id: str) -> str:
    return (
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication_id}"
        f"/ads/{ad_id}/launch-confirm"
    )


async def _prepare_confirmation(client: AsyncClient, db_session: AsyncSession, email: str):
    token = await _register(client, email)
    campaign_id, publication, ad, creative = await _setup_ready(client, db_session, token)
    readiness_response = await client.get(
        _path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert readiness_response.status_code == 200
    readiness = readiness_response.json()
    assert readiness["ready"] is True
    intent_response = await client.post(
        _intent_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
    )
    assert intent_response.status_code == 200
    intent = intent_response.json()
    body = {
        "intent_id": intent["id"],
        "confirmation_token": intent["confirmation_token"],
        "acknowledged_readiness_fingerprint": readiness["readiness_fingerprint"],
        "acknowledged_daily_budget_minor": readiness["launch_plan"]["daily_budget_minor"],
        "confirm_spend": True,
    }
    return token, campaign_id, publication, ad, creative, readiness, intent, body


@pytest.mark.asyncio
async def test_meta_launch_confirmation_activates_children_then_campaign_and_consumes_intent(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
):
    prepared = await _prepare_confirmation(
        client,
        db_session,
        "meta-launch-confirm-ok@test.com",
    )
    token, campaign_id, publication, ad, _, readiness, intent, body = prepared
    calls: list[str] = []

    class RecordingProvider:
        async def set_ad_status(self, *args, **kwargs):
            target = args[6]
            calls.append(f"ad:{target}")
            return {"status": target}

        async def set_ad_set_status(self, *args, **kwargs):
            target = args[4]
            calls.append(f"adset:{target}")
            return {"status": target}

        async def set_campaign_status(self, *args, **kwargs):
            target = args[3]
            calls.append(f"campaign:{target}")
            return {"status": target}

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_launch_confirmation.get_meta_ads_activation_provider",
        lambda: RecordingProvider(),
    )

    response = await client.post(
        _confirm_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
        json=body,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SUCCEEDED"
    assert payload["remote_ad_status"] == "ACTIVE"
    assert payload["remote_ad_set_status"] == "ACTIVE"
    assert payload["remote_campaign_status"] == "ACTIVE"
    assert payload["daily_budget_minor"] == readiness["launch_plan"]["daily_budget_minor"]
    assert calls == ["ad:ACTIVE", "adset:ACTIVE", "campaign:ACTIVE"]

    intent_result = await db_session.execute(
        select(MetaAdsLaunchIntent).where(MetaAdsLaunchIntent.id == UUID(intent["id"]))
    )
    intent_row = intent_result.scalar_one()
    assert intent_row.consumed_at is not None
    assert intent_row.activation_status == "SUCCEEDED"
    assert intent_row.activation_started_at is not None
    assert intent_row.activation_completed_at is not None
    assert intent_row.last_activation_error is None

    publication_row = (
        await db_session.execute(
            select(MetaAdsCampaignPublication).where(
                MetaAdsCampaignPublication.id == UUID(publication["id"])
            )
        )
    ).scalar_one()
    ad_set_row = (
        await db_session.execute(
            select(MetaAdsAdSetPublication).where(
                MetaAdsAdSetPublication.id == UUID(ad["ad_set_publication_id"])
            )
        )
    ).scalar_one()
    ad_row = (
        await db_session.execute(
            select(MetaAdsAdPublication).where(MetaAdsAdPublication.id == UUID(ad["id"]))
        )
    ).scalar_one()
    assert publication_row.remote_status == ad_set_row.remote_status == ad_row.remote_status == "ACTIVE"


@pytest.mark.asyncio
async def test_meta_launch_confirmation_rejects_wrong_token_without_consuming_intent(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token, campaign_id, publication, ad, _, _, intent, body = await _prepare_confirmation(
        client,
        db_session,
        "meta-launch-confirm-token@test.com",
    )
    body["confirmation_token"] = "x" * 43
    response = await client.post(
        _confirm_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
        json=body,
    )
    assert response.status_code == 403

    row = (
        await db_session.execute(
            select(MetaAdsLaunchIntent).where(MetaAdsLaunchIntent.id == UUID(intent["id"]))
        )
    ).scalar_one()
    assert row.consumed_at is None
    assert row.activation_status == "PENDING_CONFIRMATION"


@pytest.mark.asyncio
async def test_meta_launch_confirmation_rejects_expired_intent_without_external_write(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token, campaign_id, publication, ad, _, _, intent, body = await _prepare_confirmation(
        client,
        db_session,
        "meta-launch-confirm-expired@test.com",
    )
    row = (
        await db_session.execute(
            select(MetaAdsLaunchIntent).where(MetaAdsLaunchIntent.id == UUID(intent["id"]))
        )
    ).scalar_one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    response = await client.post(
        _confirm_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
        json=body,
    )
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_launch_confirmation_rejects_changed_fingerprint_without_consuming(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token, campaign_id, publication, ad, _, _, intent, body = await _prepare_confirmation(
        client,
        db_session,
        "meta-launch-confirm-stale@test.com",
    )
    ad_set = (
        await db_session.execute(
            select(MetaAdsAdSetPublication).where(
                MetaAdsAdSetPublication.id == UUID(ad["ad_set_publication_id"])
            )
        )
    ).scalar_one()
    ad_set.daily_budget_minor += 1000
    await db_session.commit()

    response = await client.post(
        _confirm_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
        json=body,
    )
    assert response.status_code == 400
    assert "readiness changed" in response.json()["detail"].lower()

    row = (
        await db_session.execute(
            select(MetaAdsLaunchIntent).where(MetaAdsLaunchIntent.id == UUID(intent["id"]))
        )
    ).scalar_one()
    assert row.consumed_at is None


@pytest.mark.asyncio
async def test_meta_launch_confirmation_rejects_budget_acknowledgement_mismatch(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token, campaign_id, publication, ad, _, _, intent, body = await _prepare_confirmation(
        client,
        db_session,
        "meta-launch-confirm-budget@test.com",
    )
    body["acknowledged_daily_budget_minor"] += 1
    response = await client.post(
        _confirm_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
        json=body,
    )
    assert response.status_code == 400

    row = (
        await db_session.execute(
            select(MetaAdsLaunchIntent).where(MetaAdsLaunchIntent.id == UUID(intent["id"]))
        )
    ).scalar_one()
    assert row.consumed_at is None


@pytest.mark.asyncio
async def test_meta_launch_confirmation_is_one_shot(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token, campaign_id, publication, ad, _, _, _, body = await _prepare_confirmation(
        client,
        db_session,
        "meta-launch-confirm-once@test.com",
    )
    path = _confirm_path(campaign_id, publication["id"], ad["id"])
    first = await client.post(path, headers=_headers(token), json=body)
    assert first.status_code == 200
    second = await client.post(path, headers=_headers(token), json=body)
    assert second.status_code == 400
    assert "consumed" in second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_launch_confirmation_rolls_back_to_paused_on_child_failure(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
):
    token, campaign_id, publication, ad, _, _, intent, body = await _prepare_confirmation(
        client,
        db_session,
        "meta-launch-confirm-rollback@test.com",
    )
    calls: list[str] = []

    class FailingProvider:
        async def set_ad_status(self, *args, **kwargs):
            target = args[6]
            calls.append(f"ad:{target}")
            return {"status": target}

        async def set_ad_set_status(self, *args, **kwargs):
            target = args[4]
            calls.append(f"adset:{target}")
            if target == "ACTIVE":
                raise MetaAdsProviderError("private failure")
            return {"status": target}

        async def set_campaign_status(self, *args, **kwargs):
            target = args[3]
            calls.append(f"campaign:{target}")
            return {"status": target}

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_launch_confirmation.get_meta_ads_activation_provider",
        lambda: FailingProvider(),
    )
    response = await client.post(
        _confirm_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
        json=body,
    )
    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Meta Ads launch failed; Campaign, Ad Set and Ad were restored to PAUSED"
    )
    assert calls == [
        "ad:ACTIVE",
        "adset:ACTIVE",
        "campaign:PAUSED",
        "adset:PAUSED",
        "ad:PAUSED",
    ]

    row = (
        await db_session.execute(
            select(MetaAdsLaunchIntent).where(MetaAdsLaunchIntent.id == UUID(intent["id"]))
        )
    ).scalar_one()
    assert row.activation_status == "FAILED"
    assert row.consumed_at is not None
    assert "restored" in row.last_activation_error


@pytest.mark.asyncio
async def test_meta_launch_confirmation_marks_unknown_when_rollback_cannot_be_verified(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
):
    token, campaign_id, publication, ad, _, _, intent, body = await _prepare_confirmation(
        client,
        db_session,
        "meta-launch-confirm-unknown@test.com",
    )

    class AmbiguousProvider:
        async def set_ad_status(self, *args, **kwargs):
            target = args[6]
            return {"status": target}

        async def set_ad_set_status(self, *args, **kwargs):
            target = args[4]
            if target == "ACTIVE":
                raise MetaAdsProviderError("activation uncertain")
            return {"status": target}

        async def set_campaign_status(self, *args, **kwargs):
            target = args[3]
            if target == "PAUSED":
                raise MetaAdsProviderError("rollback uncertain")
            return {"status": target}

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_launch_confirmation.get_meta_ads_activation_provider",
        lambda: AmbiguousProvider(),
    )
    response = await client.post(
        _confirm_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
        json=body,
    )
    assert response.status_code == 502
    assert "uncertain" in response.json()["detail"].lower()

    row = (
        await db_session.execute(
            select(MetaAdsLaunchIntent).where(MetaAdsLaunchIntent.id == UUID(intent["id"]))
        )
    ).scalar_one()
    assert row.activation_status == "UNKNOWN"
    assert row.consumed_at is not None
    assert "could not be fully verified" in row.last_activation_error


@pytest.mark.asyncio
async def test_meta_launch_confirmation_real_mode_kill_switch_blocks_before_consumption(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
):
    token, campaign_id, publication, ad, _, _, intent, body = await _prepare_confirmation(
        client,
        db_session,
        "meta-launch-confirm-kill-switch@test.com",
    )
    monkeypatch.setattr(settings, "META_ADS_MODE", "real")
    monkeypatch.setattr(settings, "META_ADS_LAUNCH_ENABLED", False)

    response = await client.post(
        _confirm_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
        json=body,
    )
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()

    row = (
        await db_session.execute(
            select(MetaAdsLaunchIntent).where(MetaAdsLaunchIntent.id == UUID(intent["id"]))
        )
    ).scalar_one()
    assert row.consumed_at is None


@pytest.mark.asyncio
async def test_meta_launch_confirmation_requires_explicit_spend_acknowledgement(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token, campaign_id, publication, ad, _, _, _, body = await _prepare_confirmation(
        client,
        db_session,
        "meta-launch-confirm-ack@test.com",
    )
    body["confirm_spend"] = False
    response = await client.post(
        _confirm_path(campaign_id, publication["id"], ad["id"]),
        headers=_headers(token),
        json=body,
    )
    assert response.status_code == 422
