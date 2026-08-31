import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "vd@test.com", "password": "Test12345!", "first_name": "VD", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "VD Product", "selling_price": 29.99}, headers=headers)
    product_id = res.json()["id"]
    camp = (await client.post(f"/api/campaigns/by-product/{product_id}", json={"name": "VD Campaign"}, headers=headers)).json()
    return token, headers, camp["id"]


@pytest.mark.asyncio
async def test_generate_visual_direction(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    response = await client.post(f"/api/campaigns/{campaign_id}/visual-direction/generate", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "visual_style" in data
    assert "tone" in data


@pytest.mark.asyncio
async def test_get_visual_direction(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    await client.post(f"/api/campaigns/{campaign_id}/visual-direction/generate", headers=headers)
    response = await client.get(f"/api/campaigns/{campaign_id}/visual-direction", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_visual_direction(client: AsyncClient):
    token, headers, campaign_id = await _setup(client)
    vd = (await client.post(f"/api/campaigns/{campaign_id}/visual-direction/generate", headers=headers)).json()
    response = await client.patch(f"/api/campaigns/visual-directions/{vd['id']}", json={
        "visual_style": "updated style"
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["visual_style"] == "updated style"


@pytest.mark.asyncio
async def test_visual_direction_isolation(client: AsyncClient):
    reg1 = await client.post("/api/auth/register", json={
        "email": "vdi1@test.com", "password": "Test12345!", "first_name": "V", "last_name": "1",
    })
    h1 = {"Authorization": f"Bearer {reg1.json()['access_token']}"}
    p1 = (await client.post("/api/products", json={"name": "P1", "selling_price": 10}, headers=h1)).json()
    c1 = (await client.post(f"/api/campaigns/by-product/{p1['id']}", json={"name": "C1"}, headers=h1)).json()
    await client.post(f"/api/campaigns/{c1['id']}/visual-direction/generate", headers=h1)

    reg2 = await client.post("/api/auth/register", json={
        "email": "vdi2@test.com", "password": "Test12345!", "first_name": "V", "last_name": "2",
    })
    h2 = {"Authorization": f"Bearer {reg2.json()['access_token']}"}
    response = await client.get(f"/api/campaigns/{c1['id']}/visual-direction", headers=h2)
    assert response.status_code == 404
