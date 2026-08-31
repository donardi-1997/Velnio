import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "enrich@test.com", "password": "Test12345!", "first_name": "Enrich", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Enrich Product", "selling_price": 39.99}, headers=headers)
    return token, headers, res.json()["id"]


@pytest.mark.asyncio
async def test_enrich_product(client: AsyncClient):
    token, headers, product_id = await _setup(client)
    response = await client.post(f"/api/products/{product_id}/enrich", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "features" in data
    assert "benefits" in data


@pytest.mark.asyncio
async def test_get_enrichment(client: AsyncClient):
    token, headers, product_id = await _setup(client)
    await client.post(f"/api/products/{product_id}/enrich", headers=headers)
    response = await client.get(f"/api/products/{product_id}/enrichment", headers=headers)
    assert response.status_code == 200
    assert "features" in response.json()


@pytest.mark.asyncio
async def test_enrichment_consumes_credits(client: AsyncClient):
    token, headers, product_id = await _setup(client)
    wallet_before = (await client.get("/api/credits", headers=headers)).json()["balance"]
    await client.post(f"/api/products/{product_id}/enrich", headers=headers)
    wallet_after = (await client.get("/api/credits", headers=headers)).json()["balance"]
    assert wallet_after < wallet_before
