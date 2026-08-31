import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "shopify@test.com", "password": "Test12345!", "first_name": "Shopify", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Shopify Product", "selling_price": 29.99}, headers=headers)
    return token, res.json()["id"]


@pytest.mark.asyncio
async def test_mock_publish(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(f"/api/products/{product_id}/publish", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "published"
    assert data["provider"] == "mock"
    assert "shopify_product_id" in data
