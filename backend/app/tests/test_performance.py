import pytest
import uuid
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "perf@test.com", "password": "Test12345!", "first_name": "Perf", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Perf Product", "selling_price": 29.99}, headers=headers)
    product_id = res.json()["id"]
    camp = (await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Perf Campaign", "selling_price": 29.99
    }, headers=headers)).json()
    return token, headers, camp["id"]


@pytest.mark.asyncio
async def test_empty_metrics(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    response = await client.get(f"/api/campaigns/{campaign_id}/performance", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["sessions"] == 0
    assert data["conversion_rate"] == 0.0
    assert data["aov"] == 0.0


@pytest.mark.asyncio
async def test_timeline_empty(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    response = await client.get(f"/api/campaigns/{campaign_id}/performance/timeline", headers=headers)
    assert response.status_code == 200
    assert response.json()["timeline"] == []


@pytest.mark.asyncio
async def test_variant_performance(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    response = await client.get(f"/api/campaigns/{campaign_id}/variants/performance", headers=headers)
    assert response.status_code == 200
    assert "variants" in response.json()


@pytest.mark.asyncio
async def test_angle_performance(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    response = await client.get(f"/api/campaigns/{campaign_id}/angles/performance", headers=headers)
    assert response.status_code == 200
    assert "angles" in response.json()
