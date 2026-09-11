from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meta_ads import MetaAdsCampaignPublication


async def _register(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Test12345!",
            "first_name": "Meta",
            "last_name": "Configurator",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _campaign(client: AsyncClient, token: str) -> str:
    response = await client.post(
        "/api/campaigns",
        headers=_headers(token),
        json={"name": "Delivery config campaign", "target_country": "CO", "currency": "COP"},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _publication(client: AsyncClient, token: str, campaign_id: str) -> dict:
    headers = _headers(token)
    connect = await client.post("/api/meta-ads/connect-mock", headers=headers)
    assert connect.status_code == 200
    response = await client.post(
        f"/api/campaigns/{campaign_id}/meta-ads/publish",
        headers=headers,
        json={"ad_account_id": "act_1000000001"},
    )
    assert response.status_code == 200
    return response.json()


def _valid_config() -> dict[str, str]:
    return {
        "pixel_id": "1000000001501",
        "page_id": "1000000001601",
        "instagram_account_id": "1000000001701",
    }


@pytest.mark.asyncio
async def test_meta_delivery_config_is_validated_and_persisted(client: AsyncClient):
    token = await _register(client, "delivery-config@test.com")
    campaign_id = await _campaign(client, token)
    publication = await _publication(client, token, campaign_id)

    response = await client.patch(
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication['id']}/delivery-config",
        headers=_headers(token),
        json=_valid_config(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["remote_status"] == "PAUSED"
    assert payload["pixel_id"] == "1000000001501"
    assert payload["page_id"] == "1000000001601"
    assert payload["instagram_account_id"] == "1000000001701"
    assert payload["delivery_configured_at"] is not None

    listed = await client.get(
        f"/api/campaigns/{campaign_id}/meta-ads/publications",
        headers=_headers(token),
    )
    assert listed.status_code == 200
    assert listed.json()[0]["pixel_id"] == "1000000001501"
    assert listed.json()[0]["page_id"] == "1000000001601"


@pytest.mark.asyncio
async def test_meta_delivery_config_allows_optional_instagram(client: AsyncClient):
    token = await _register(client, "delivery-no-instagram@test.com")
    campaign_id = await _campaign(client, token)
    publication = await _publication(client, token, campaign_id)
    config = _valid_config()
    config["instagram_account_id"] = None

    response = await client.patch(
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication['id']}/delivery-config",
        headers=_headers(token),
        json=config,
    )

    assert response.status_code == 200
    assert response.json()["instagram_account_id"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value", "detail"),
    [
        ("pixel_id", "999999", "pixel"),
        ("page_id", "999999", "page"),
        ("instagram_account_id", "999999", "instagram"),
    ],
)
async def test_meta_delivery_config_rejects_resources_not_owned_by_account(
    client: AsyncClient,
    field: str,
    value: str,
    detail: str,
):
    token = await _register(client, f"delivery-invalid-{field}@test.com")
    campaign_id = await _campaign(client, token)
    publication = await _publication(client, token, campaign_id)
    config = _valid_config()
    config[field] = value

    response = await client.patch(
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication['id']}/delivery-config",
        headers=_headers(token),
        json=config,
    )

    assert response.status_code == 403
    assert detail in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_meta_delivery_config_rejects_malformed_resource_ids(client: AsyncClient):
    token = await _register(client, "delivery-malformed@test.com")
    campaign_id = await _campaign(client, token)
    publication = await _publication(client, token, campaign_id)

    response = await client.patch(
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication['id']}/delivery-config",
        headers=_headers(token),
        json={"pixel_id": "../../me", "page_id": "1000000001601"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_meta_delivery_config_is_workspace_isolated(client: AsyncClient):
    owner_token = await _register(client, "delivery-owner@test.com")
    other_token = await _register(client, "delivery-other@test.com")
    campaign_id = await _campaign(client, owner_token)
    publication = await _publication(client, owner_token, campaign_id)
    await client.post("/api/meta-ads/connect-mock", headers=_headers(other_token))

    response = await client.patch(
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication['id']}/delivery-config",
        headers=_headers(other_token),
        json=_valid_config(),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_meta_delivery_config_refuses_non_paused_publication(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = await _register(client, "delivery-active@test.com")
    campaign_id = await _campaign(client, token)
    publication = await _publication(client, token, campaign_id)

    result = await db_session.execute(
        select(MetaAdsCampaignPublication).where(
            MetaAdsCampaignPublication.id == UUID(publication["id"])
        )
    )
    row = result.scalar_one()
    row.remote_status = "ACTIVE"
    await db_session.commit()

    response = await client.patch(
        f"/api/campaigns/{campaign_id}/meta-ads/publications/{publication['id']}/delivery-config",
        headers=_headers(token),
        json=_valid_config(),
    )

    assert response.status_code == 403
    assert "paused" in response.json()["detail"].lower()
