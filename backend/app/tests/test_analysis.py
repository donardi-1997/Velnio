import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> str:
    reg = await client.post("/api/auth/register", json={
        "email": "analysis@test.com", "password": "Test12345!", "first_name": "Analysis", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Analyze Product", "selling_price": 29.99}, headers=headers)
    product_id = res.json()["id"]
    return token, product_id


@pytest.mark.asyncio
async def test_analyze_product(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(f"/api/products/{product_id}/analyze", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["overall_score"] <= 100
    assert len(data["strengths"]) > 0


@pytest.mark.asyncio
async def test_credit_consumption(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "credits@test.com", "password": "Test12345!", "first_name": "Credits", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    wallet_before = (await client.get("/api/credits", headers=headers)).json()["balance"]
    
    res = await client.post("/api/products", json={"name": "Credit Test", "selling_price": 19.99}, headers=headers)
    product_id = res.json()["id"]
    await client.post(f"/api/products/{product_id}/analyze", headers=headers)
    
    wallet_after = (await client.get("/api/credits", headers=headers)).json()["balance"]
    assert wallet_after == wallet_before - 1
