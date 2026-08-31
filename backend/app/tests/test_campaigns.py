import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "campaigns@test.com", "password": "Test12345!", "first_name": "Campaigns", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Campaign Product", "selling_price": 49.99}, headers=headers)
    product_id = res.json()["id"]
    return token, product_id


@pytest.mark.asyncio
async def test_create_campaign(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Test Campaign",
        "target_country": "US",
        "selling_price": 49.99,
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Campaign"
    assert data["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_list_campaigns(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Campaign A",
    }, headers=headers)
    response = await client.get("/api/campaigns", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_campaign(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Get Campaign",
    }, headers=headers)
    campaign_id = create.json()["id"]
    response = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Get Campaign"


@pytest.mark.asyncio
async def test_update_campaign(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Old Name",
    }, headers=headers)
    campaign_id = create.json()["id"]
    response = await client.patch(f"/api/campaigns/{campaign_id}", json={
        "name": "New Name",
        "target_audience": "Dog owners",
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["target_audience"] == "Dog owners"


@pytest.mark.asyncio
async def test_delete_campaign(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Delete Me",
    }, headers=headers)
    campaign_id = create.json()["id"]
    response = await client.delete(f"/api/campaigns/{campaign_id}", headers=headers)
    assert response.status_code == 204
    get_response = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_generate_campaign_angles(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Angle Campaign",
        "target_country": "US",
    }, headers=headers)
    campaign_id = create.json()["id"]
    response = await client.post(f"/api/campaigns/{campaign_id}/angles/generate", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all("campaign_id" in a for a in data)


@pytest.mark.asyncio
async def test_select_campaign_angle(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Select Campaign",
    }, headers=headers)
    campaign_id = create.json()["id"]
    angles = (await client.post(f"/api/campaigns/{campaign_id}/angles/generate", headers=headers)).json()
    angle_id = angles[0]["id"]
    response = await client.post(f"/api/campaigns/{campaign_id}/angles/{angle_id}/select", headers=headers)
    assert response.status_code == 200
    assert response.json()["selected"] is True


@pytest.mark.asyncio
async def test_generate_campaign_offer(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Offer Campaign",
        "selling_price": 39.99,
    }, headers=headers)
    campaign_id = create.json()["id"]
    angles = (await client.post(f"/api/campaigns/{campaign_id}/angles/generate", headers=headers)).json()
    await client.post(f"/api/campaigns/{campaign_id}/angles/{angles[0]['id']}/select", headers=headers)
    response = await client.post(f"/api/campaigns/{campaign_id}/offer/generate", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "headline" in data
    assert data["campaign_id"] == campaign_id


@pytest.mark.asyncio
async def test_generate_campaign_landing(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Landing Campaign",
        "selling_price": 39.99,
    }, headers=headers)
    campaign_id = create.json()["id"]
    angles = (await client.post(f"/api/campaigns/{campaign_id}/angles/generate", headers=headers)).json()
    await client.post(f"/api/campaigns/{campaign_id}/angles/{angles[0]['id']}/select", headers=headers)
    response = await client.post(f"/api/campaigns/{campaign_id}/landing/generate", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["campaign_id"] == campaign_id


@pytest.mark.asyncio
async def test_publish_campaign(client: AsyncClient):
    token, product_id = await _setup(client)
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Publish Campaign",
        "selling_price": 29.99,
    }, headers=headers)
    campaign_id = create.json()["id"]
    angles = (await client.post(f"/api/campaigns/{campaign_id}/angles/generate", headers=headers)).json()
    await client.post(f"/api/campaigns/{campaign_id}/angles/{angles[0]['id']}/select", headers=headers)
    await client.post(f"/api/campaigns/{campaign_id}/landing/generate", headers=headers)
    response = await client.post(f"/api/campaigns/{campaign_id}/publish", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "published"
    assert data["provider"] == "mock"


@pytest.mark.asyncio
async def test_workspace_isolation(client: AsyncClient):
    reg1 = await client.post("/api/auth/register", json={
        "email": "ws1@test.com", "password": "Test12345!", "first_name": "W", "last_name": "1",
    })
    headers1 = {"Authorization": f"Bearer {reg1.json()['access_token']}"}
    prod1 = (await client.post("/api/products", json={"name": "P1", "selling_price": 10}, headers=headers1)).json()
    camp1 = (await client.post(f"/api/campaigns/by-product/{prod1['id']}", json={"name": "C1"}, headers=headers1)).json()

    reg2 = await client.post("/api/auth/register", json={
        "email": "ws2@test.com", "password": "Test12345!", "first_name": "W", "last_name": "2",
    })
    headers2 = {"Authorization": f"Bearer {reg2.json()['access_token']}"}

    response = await client.get(f"/api/campaigns/{camp1['id']}", headers=headers2)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_campaign_access(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "unauth@test.com", "password": "Test12345!", "first_name": "U", "last_name": "A",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    prod = (await client.post("/api/products", json={"name": "UP", "selling_price": 10}, headers=headers)).json()
    camp = (await client.post(f"/api/campaigns/by-product/{prod['id']}", json={"name": "UC"}, headers=headers)).json()

    other_reg = await client.post("/api/auth/register", json={
        "email": "other@test.com", "password": "Test12345!", "first_name": "O", "last_name": "X",
    })
    other_headers = {"Authorization": f"Bearer {other_reg.json()['access_token']}"}
    response = await client.get(f"/api/campaigns/{camp['id']}", headers=other_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_campaign(client: AsyncClient):
    import uuid
    reg = await client.post("/api/auth/register", json={
        "email": "none@test.com", "password": "Test12345!", "first_name": "N", "last_name": "X",
    })
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    response = await client.get(f"/api/campaigns/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404
