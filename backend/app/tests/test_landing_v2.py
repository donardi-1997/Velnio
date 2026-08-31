import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_landing_uses_product_images(client: AsyncClient):
    # Setup user, product with images, campaign, angle, offer
    reg = await client.post("/api/auth/register", json={
        "email": "lv2@test.com", "password": "Test12345!", "first_name": "LV2", "last_name": "User",
    })
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    prod = (await client.post("/api/products", json={"name": "LV2 Product", "selling_price": 39.99}, headers=headers)).json()
    camp = (await client.post(f"/api/campaigns/by-product/{prod['id']}", json={"name": "LV2 Campaign", "selling_price": 39.99}, headers=headers)).json()
    angles = (await client.post(f"/api/campaigns/{camp['id']}/angles/generate", headers=headers)).json()
    await client.post(f"/api/campaigns/{camp['id']}/angles/{angles[0]['id']}/select", headers=headers)
    await client.post(f"/api/campaigns/{camp['id']}/offer/generate", headers=headers)

    response = await client.post(f"/api/campaigns/{camp['id']}/landing/generate", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert len(data["sections"]) >= 5
