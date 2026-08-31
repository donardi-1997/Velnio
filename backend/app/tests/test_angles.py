import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "angles@test.com", "password": "Test12345!", "first_name": "Angles", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Angle Product", "selling_price": 29.99}, headers=headers)
    return token, res.json()["id"]


@pytest.mark.asyncio
async def test_generate_angles(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(f"/api/products/{product_id}/angles/generate", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all("name" in a for a in data)


@pytest.mark.asyncio
async def test_select_angle(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    angles = (await client.post(f"/api/products/{product_id}/angles/generate", headers=headers)).json()
    angle_id = angles[0]["id"]
    response = await client.post(f"/api/products/{product_id}/angles/{angle_id}/select", headers=headers)
    assert response.status_code == 200
    assert response.json()["selected"] is True


@pytest.mark.asyncio
async def test_only_one_selected(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    angles = (await client.post(f"/api/products/{product_id}/angles/generate", headers=headers)).json()
    
    await client.post(f"/api/products/{product_id}/angles/{angles[0]['id']}/select", headers=headers)
    await client.post(f"/api/products/{product_id}/angles/{angles[1]['id']}/select", headers=headers)
    
    all_angles = (await client.get(f"/api/products/{product_id}/angles", headers=headers)).json()
    selected = [a for a in all_angles if a["selected"]]
    assert len(selected) == 1
    assert selected[0]["id"] == angles[1]["id"]
