import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meta_ads import MetaAdsCampaignPublication, MetaAdsConnection
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError


async def _register(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Test12345!",
            "first_name": "Meta",
            "last_name": "Publisher",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_campaign(client: AsyncClient, token: str, name: str = "Meta launch") -> str:
    response = await client.post(
        "/api/campaigns",
        headers=_headers(token),
        json={"name": name, "target_country": "CO", "currency": "COP"},
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_meta_campaign_publish_creates_paused_remote_campaign(client: AsyncClient):
    token = await _register(client, "meta-publish@test.com")
    headers = _headers(token)
    campaign_id = await _create_campaign(client, token)
    connect = await client.post("/api/meta-ads/connect-mock", headers=headers)
    assert connect.status_code == 200

    response = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publish",
        headers=headers,
        json={"ad_account_id": "act_1000000001"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["campaign_id"] == campaign_id
    assert payload["ad_account_id"] == "act_1000000001"
    assert payload["remote_status"] == "PAUSED"
    assert payload["objective"] == "OUTCOME_SALES"
    assert payload["remote_campaign_id"].startswith("mock_meta_campaign_")
    assert f"[VELNIO:{campaign_id}]" in payload["remote_campaign_name"]
    assert payload["reused"] is False


@pytest.mark.asyncio
async def test_meta_campaign_repeat_publish_is_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-idempotent@test.com")
    headers = _headers(token)
    campaign_id = await _create_campaign(client, token, "Idempotent Meta launch")
    await client.post("/api/meta-ads/connect-mock", headers=headers)

    first = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publish",
        headers=headers,
        json={"ad_account_id": "act_1000000001"},
    )
    second = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publish",
        headers=headers,
        json={"ad_account_id": "act_1000000001"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["remote_campaign_id"] == first.json()["remote_campaign_id"]
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["reused"] is True

    result = await db_session.execute(
        select(MetaAdsCampaignPublication).where(
            MetaAdsCampaignPublication.campaign_id == campaign_id,
            MetaAdsCampaignPublication.ad_account_id == "act_1000000001",
        )
    )
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_meta_campaign_publications_can_be_listed(client: AsyncClient):
    token = await _register(client, "meta-list-publications@test.com")
    headers = _headers(token)
    campaign_id = await _create_campaign(client, token)
    await client.post("/api/meta-ads/connect-mock", headers=headers)
    await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publish",
        headers=headers,
        json={"ad_account_id": "act_1000000001"},
    )

    response = await client.get(
        f"/api/campaigns/{campaign_id}/meta-ads/publications",
        headers=headers,
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["remote_status"] == "PAUSED"


@pytest.mark.asyncio
async def test_meta_campaign_publish_rejects_inaccessible_ad_account(client: AsyncClient):
    token = await _register(client, "meta-inaccessible@test.com")
    headers = _headers(token)
    campaign_id = await _create_campaign(client, token)
    await client.post("/api/meta-ads/connect-mock", headers=headers)

    response = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publish",
        headers=headers,
        json={"ad_account_id": "act_9999999999"},
    )
    assert response.status_code == 403
    assert "not accessible" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_campaign_publish_rejects_malformed_ad_account(client: AsyncClient):
    token = await _register(client, "meta-malformed-account@test.com")
    campaign_id = await _create_campaign(client, token)

    response = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publish",
        headers=_headers(token),
        json={"ad_account_id": "https://evil.example/account"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_meta_campaign_publish_requires_management_scope(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "meta-read-only@test.com")
    headers = _headers(token)
    campaign_id = await _create_campaign(client, token)
    await client.post("/api/meta-ads/connect-mock", headers=headers)

    result = await db_session.execute(
        select(MetaAdsConnection).where(MetaAdsConnection.is_active == True)
    )
    connection = result.scalar_one()
    connection.scopes = "ads_read"
    await db_session.commit()

    response = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publish",
        headers=headers,
        json={"ad_account_id": "act_1000000001"},
    )
    assert response.status_code == 403
    assert "ads_management" in response.json()["detail"]
    assert "reconnect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_campaign_publish_is_workspace_isolated(client: AsyncClient):
    owner_token = await _register(client, "meta-owner-one@test.com")
    other_token = await _register(client, "meta-owner-two@test.com")
    campaign_id = await _create_campaign(client, owner_token)
    await client.post("/api/meta-ads/connect-mock", headers=_headers(other_token))

    response = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publish",
        headers=_headers(other_token),
        json={"ad_account_id": "act_1000000001"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_meta_campaign_provider_failure_is_sanitized(
    client: AsyncClient,
    monkeypatch,
):
    token = await _register(client, "meta-provider-failure@test.com")
    headers = _headers(token)
    campaign_id = await _create_campaign(client, token)
    await client.post("/api/meta-ads/connect-mock", headers=headers)

    class FailingProvider:
        async def ensure_paused_campaign(self, *args, **kwargs):
            raise MetaAdsProviderError("secret upstream payload")

    monkeypatch.setattr(
        "app.modules.campaigns.application.meta_ads_publishing.get_meta_ads_provider",
        lambda: FailingProvider(),
    )

    response = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publish",
        headers=headers,
        json={"ad_account_id": "act_1000000001"},
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "Meta Ads campaign creation failed"
    assert "secret upstream payload" not in response.text
