import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "landings@test.com", "password": "Test12345!", "first_name": "Landings", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Landing Product", "selling_price": 39.99}, headers=headers)
    product_id = res.json()["id"]
    
    angles = (await client.post(f"/api/products/{product_id}/angles/generate", headers=headers)).json()
    await client.post(f"/api/products/{product_id}/angles/{angles[0]['id']}/select", headers=headers)
    return token, product_id


@pytest.mark.asyncio
async def test_generate_landing(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(f"/api/products/{product_id}/landing/generate", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert len(data["sections"]) > 0


@pytest.mark.asyncio
async def test_update_section(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    landing = (await client.post(f"/api/products/{product_id}/landing/generate", headers=headers)).json()
    section_id = landing["sections"][0]["id"]
    
    response = await client.patch(f"/api/products/landing-sections/{section_id}", json={
        "content": {"headline": "Updated headline", "subheadline": "Updated subheadline", "cta_text": "Buy now"}
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["content"]["headline"] == "Updated headline"
