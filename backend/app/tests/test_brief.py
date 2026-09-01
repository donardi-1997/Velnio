import pytest
from httpx import AsyncClient
from uuid import uuid4


async def _get_token(client: AsyncClient) -> str:
    await client.post("/api/auth/register", json={"email": "test@example.com", "password": "testpass123", "first_name": "Test", "last_name": "User"})
    response = await client.post("/api/auth/login", json={"email": "test@example.com", "password": "testpass123"})
    return response.json()["access_token"]


async def _create_product_and_campaign(client: AsyncClient, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    product_res = await client.post("/api/products", json={
        "name": "Test Product",
        "source_type": "MANUAL",
        "target_country": "US",
        "target_language": "en",
        "currency": "USD",
        "selling_price": 29.99,
    }, headers=headers)
    product_id = product_res.json()["id"]
    campaign_res = await client.post("/api/campaigns", json={
        "product_id": product_id,
        "name": "Test Campaign",
        "target_country": "US",
        "target_language": "en",
        "currency": "USD",
        "selling_price": 29.99,
    }, headers=headers)
    campaign_id = campaign_res.json()["id"]
    return product_id, campaign_id


@pytest.mark.asyncio
async def test_generate_brief(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    product_id, campaign_id = await _create_product_and_campaign(client, token)
    response = await client.post(f"/api/campaigns/{campaign_id}/generate-brief", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["product_summary"] is not None
    assert data["target_audience"] is not None
    assert data["key_benefits"] is not None
    assert data["tone_of_voice"] is not None
    assert data["pricing_strategy"] is not None
    assert data["positioning"] is not None
    assert data["campaign_id"] == campaign_id


@pytest.mark.asyncio
async def test_generate_brief_campaign_not_found(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(f"/api/campaigns/{uuid4()}/generate-brief", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_brief_updates_existing(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    product_id, campaign_id = await _create_product_and_campaign(client, token)
    res1 = await client.post(f"/api/campaigns/{campaign_id}/generate-brief", headers=headers)
    assert res1.status_code == 200
    brief_id_1 = res1.json()["id"]
    res2 = await client.post(f"/api/campaigns/{campaign_id}/generate-brief", headers=headers)
    assert res2.status_code == 200
    brief_id_2 = res2.json()["id"]
    assert brief_id_1 == brief_id_2
