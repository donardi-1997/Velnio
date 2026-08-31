import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "pub@test.com", "password": "Test12345!", "first_name": "Pub", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Pub Product", "selling_price": 29.99}, headers=headers)
    product_id = res.json()["id"]
    return token, headers, product_id


@pytest.mark.asyncio
async def test_readiness_fails_when_empty(client: AsyncClient):
    token, headers, product_id = await _setup(client)
    camp = (await client.post(f"/api/campaigns/by-product/{product_id}", json={"name": "Empty Campaign"}, headers=headers)).json()
    response = await client.get(f"/api/campaigns/{camp['id']}/publish-readiness", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is False
    assert len(data["checks"]) > 0


@pytest.mark.asyncio
async def test_readiness_succeeds_when_complete(client: AsyncClient):
    token, headers, product_id = await _setup(client)
    camp = (await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Full Campaign", "selling_price": 29.99, "supplier_price": 9.99
    }, headers=headers)).json()

    angles = (await client.post(f"/api/campaigns/{camp['id']}/angles/generate", headers=headers)).json()
    await client.post(f"/api/campaigns/{camp['id']}/angles/{angles[0]['id']}/select", headers=headers)
    await client.post(f"/api/campaigns/{camp['id']}/offer/generate", headers=headers)
    await client.post(f"/api/campaigns/{camp['id']}/landing/generate", headers=headers)
    await client.post(f"/api/campaigns/{camp['id']}/visual-direction/generate", headers=headers)

    response = await client.get(f"/api/campaigns/{camp['id']}/publish-readiness", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "ready" in data
    assert "checks" in data
    assert len(data["checks"]) >= 5
    # Core checks should pass: product, angle, offer, landing, visual direction, prices
    passed_names = [c["check"] for c in data["checks"] if c["status"] == "passed"]
    assert "product_exists" in passed_names
    assert "angle_selected" in passed_names
    assert "offer_exists" in passed_names
    assert "landing_ready" in passed_names
    assert "has_visual_direction" in passed_names
    assert "prices_set" in passed_names
