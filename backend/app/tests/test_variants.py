import pytest
import uuid
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "variants@test.com", "password": "Test12345!", "first_name": "Var", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Var Product", "selling_price": 29.99}, headers=headers)
    product_id = res.json()["id"]
    camp = (await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Var Campaign", "selling_price": 29.99
    }, headers=headers)).json()
    return token, headers, camp["id"]


@pytest.mark.asyncio
async def test_create_control_automatically(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    # Generate angles and landing to create control variant
    angles = (await client.post(f"/api/campaigns/{campaign_id}/angles/generate", headers=headers)).json()
    await client.post(f"/api/campaigns/{campaign_id}/angles/{angles[0]['id']}/select", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/offer/generate", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/landing/generate", headers=headers)

    response = await client.post(f"/api/campaigns/{campaign_id}/variants", json={
        "name": "Control",
        "clone_from_variant_id": None,
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["variant_key"] == "B"
    assert data["name"] == "Control"


@pytest.mark.asyncio
async def test_clone_variant(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    angles = (await client.post(f"/api/campaigns/{campaign_id}/angles/generate", headers=headers)).json()
    await client.post(f"/api/campaigns/{campaign_id}/angles/{angles[0]['id']}/select", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/offer/generate", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/landing/generate", headers=headers)

    # Create variant B
    variant_b = (await client.post(f"/api/campaigns/{campaign_id}/variants", json={
        "name": "Variant B",
    }, headers=headers)).json()

    # Clone to variant C
    response = await client.post(f"/api/campaigns/{campaign_id}/variants", json={
        "name": "Variant C",
        "clone_from_variant_id": variant_b["id"],
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["variant_key"] == "C"


@pytest.mark.asyncio
async def test_traffic_weights_sum_100(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    angles = (await client.post(f"/api/campaigns/{campaign_id}/angles/generate", headers=headers)).json()
    await client.post(f"/api/campaigns/{campaign_id}/angles/{angles[0]['id']}/select", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/offer/generate", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/landing/generate", headers=headers)

    variant_a = (await client.post(f"/api/campaigns/{campaign_id}/variants", json={"name": "A"}, headers=headers)).json()
    variant_b = (await client.post(f"/api/campaigns/{campaign_id}/variants", json={"name": "B"}, headers=headers)).json()

    response = await client.patch(f"/api/campaigns/{campaign_id}/variants/traffic", json={
        "weights": {variant_a["id"]: 50, variant_b["id"]: 50}
    }, headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_reject_invalid_weights(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    angles = (await client.post(f"/api/campaigns/{campaign_id}/angles/generate", headers=headers)).json()
    await client.post(f"/api/campaigns/{campaign_id}/angles/{angles[0]['id']}/select", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/offer/generate", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/landing/generate", headers=headers)

    variant_a = (await client.post(f"/api/campaigns/{campaign_id}/variants", json={"name": "A"}, headers=headers)).json()
    variant_b = (await client.post(f"/api/campaigns/{campaign_id}/variants", json={"name": "B"}, headers=headers)).json()

    response = await client.patch(f"/api/campaigns/{campaign_id}/variants/traffic", json={
        "weights": {variant_a["id"]: 60, variant_b["id"]: 60}
    }, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_max_active_variants(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    angles = (await client.post(f"/api/campaigns/{campaign_id}/angles/generate", headers=headers)).json()
    await client.post(f"/api/campaigns/{campaign_id}/angles/{angles[0]['id']}/select", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/offer/generate", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/landing/generate", headers=headers)

    # Create 4 variants
    for i in range(4):
        await client.post(f"/api/campaigns/{campaign_id}/variants", json={"name": f"V{i}"}, headers=headers)

    # 5th should fail
    response = await client.post(f"/api/campaigns/{campaign_id}/variants", json={"name": "V4"}, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_variants(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    angles = (await client.post(f"/api/campaigns/{campaign_id}/angles/generate", headers=headers)).json()
    await client.post(f"/api/campaigns/{campaign_id}/angles/{angles[0]['id']}/select", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/offer/generate", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/landing/generate", headers=headers)

    await client.post(f"/api/campaigns/{campaign_id}/variants", json={"name": "A"}, headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/variants", json={"name": "B"}, headers=headers)

    response = await client.get(f"/api/campaigns/{campaign_id}/variants", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
