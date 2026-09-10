import pytest
from httpx import AsyncClient


async def _setup_campaign(client: AsyncClient):
    registered = await client.post(
        "/api/auth/register",
        json={
            "email": "traffic-distribution@test.com",
            "password": "Test12345!",
            "first_name": "Traffic",
            "last_name": "User",
        },
    )
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    product = await client.post(
        "/api/products",
        json={"name": "Traffic Product", "selling_price": 39.99},
        headers=headers,
    )
    campaign = await client.post(
        f"/api/campaigns/by-product/{product.json()['id']}",
        json={"name": "Traffic Campaign", "selling_price": 39.99},
        headers=headers,
    )
    campaign_id = campaign.json()["id"]
    angles = (
        await client.post(
            f"/api/campaigns/{campaign_id}/angles/generate",
            headers=headers,
        )
    ).json()
    await client.post(
        f"/api/campaigns/{campaign_id}/angles/{angles[0]['id']}/select",
        headers=headers,
    )
    await client.post(f"/api/campaigns/{campaign_id}/offer/generate", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/landing/generate", headers=headers)
    return headers, campaign_id


@pytest.mark.asyncio
async def test_traffic_update_zeroes_omitted_variants(client: AsyncClient):
    headers, campaign_id = await _setup_campaign(client)
    variants = (
        await client.get(f"/api/campaigns/{campaign_id}/variants", headers=headers)
    ).json()
    control = next(item for item in variants if item["variant_key"] == "A")
    assert control["traffic_weight"] == 100

    challenger = (
        await client.post(
            f"/api/campaigns/{campaign_id}/variants",
            json={"name": "Challenger", "clone_from_variant_id": control["id"]},
            headers=headers,
        )
    ).json()

    response = await client.patch(
        f"/api/campaigns/{campaign_id}/variants/traffic",
        json={"weights": {challenger["id"]: 100}},
        headers=headers,
    )
    assert response.status_code == 200

    updated = (
        await client.get(f"/api/campaigns/{campaign_id}/variants", headers=headers)
    ).json()
    updated_control = next(item for item in updated if item["id"] == control["id"])
    updated_challenger = next(item for item in updated if item["id"] == challenger["id"])
    assert updated_control["traffic_weight"] == 0
    assert updated_control["status"] == "PAUSED"
    assert updated_challenger["traffic_weight"] == 100
    assert updated_challenger["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_archived_variant_cannot_receive_traffic(client: AsyncClient):
    headers, campaign_id = await _setup_campaign(client)
    variants = (
        await client.get(f"/api/campaigns/{campaign_id}/variants", headers=headers)
    ).json()
    control = next(item for item in variants if item["variant_key"] == "A")
    challenger = (
        await client.post(
            f"/api/campaigns/{campaign_id}/variants",
            json={"name": "Archived Challenger", "clone_from_variant_id": control["id"]},
            headers=headers,
        )
    ).json()
    await client.patch(
        f"/api/campaigns/{campaign_id}/variants/{challenger['id']}",
        json={"status": "ARCHIVED"},
        headers=headers,
    )

    response = await client.patch(
        f"/api/campaigns/{campaign_id}/variants/traffic",
        json={"weights": {challenger["id"]: 100}},
        headers=headers,
    )
    assert response.status_code == 400
