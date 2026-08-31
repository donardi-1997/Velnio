import pytest
import uuid
from httpx import AsyncClient
from app.services.demo import DemoEventGenerator


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "demo@test.com", "password": "Test12345!", "first_name": "Demo", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Demo Product", "selling_price": 29.99}, headers=headers)
    product_id = res.json()["id"]
    camp = (await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Demo Campaign", "selling_price": 29.99
    }, headers=headers)).json()
    return token, headers, camp["id"]


@pytest.mark.asyncio
async def test_demo_events_generates_events(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    angles = (await client.post(f"/api/campaigns/{campaign_id}/angles/generate", headers=headers)).json()
    await client.post(f"/api/campaigns/{campaign_id}/angles/{angles[0]['id']}/select", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/offer/generate", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/landing/generate", headers=headers)

    variant_a = (await client.post(f"/api/campaigns/{campaign_id}/variants", json={"name": "A"}, headers=headers)).json()
    variant_b = (await client.post(f"/api/campaigns/{campaign_id}/variants", json={"name": "B"}, headers=headers)).json()

    response = await client.post(f"/api/campaigns/{campaign_id}/demo/events", json={
        "variant_a_sessions": 100,
        "variant_b_sessions": 100,
        "variant_a_purchases": 5,
        "variant_b_purchases": 8,
        "days_back": 7,
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_events"] > 0


@pytest.mark.asyncio
async def test_demo_events_requires_2_variants(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    response = await client.post(f"/api/campaigns/{campaign_id}/demo/events", json={
        "variant_a_sessions": 100,
        "variant_b_sessions": 100,
    }, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_clear_demo_events(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    angles = (await client.post(f"/api/campaigns/{campaign_id}/angles/generate", headers=headers)).json()
    await client.post(f"/api/campaigns/{campaign_id}/angles/{angles[0]['id']}/select", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/offer/generate", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/landing/generate", headers=headers)

    await client.post(f"/api/campaigns/{campaign_id}/variants", json={"name": "A"}, headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/variants", json={"name": "B"}, headers=headers)

    await client.post(f"/api/campaigns/{campaign_id}/demo/events", json={
        "variant_a_sessions": 50,
        "variant_b_sessions": 50,
    }, headers=headers)

    response = await client.delete(f"/api/campaigns/{campaign_id}/demo/events", headers=headers)
    assert response.status_code == 200
    assert response.json()["cleared"] > 0
