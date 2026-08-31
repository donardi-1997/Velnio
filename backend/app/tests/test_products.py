import pytest
from httpx import AsyncClient


async def _get_token(client: AsyncClient) -> str:
    reg = await client.post("/api/auth/register", json={
        "email": "prod@test.com",
        "password": "Test12345!",
        "first_name": "Prod",
        "last_name": "User",
    })
    return reg.json()["access_token"]


@pytest.mark.asyncio
async def test_create_product(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/api/products", json={
        "name": "Test Product",
        "selling_price": 29.99,
        "supplier_price": 9.99,
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Product"
    assert data["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_list_products(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/products", json={"name": "List Product"}, headers=headers)
    response = await client.get("/api/products", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_workspace_isolation(client: AsyncClient):
    reg1 = await client.post("/api/auth/register", json={
        "email": "iso1@test.com", "password": "Test12345!", "first_name": "Iso", "last_name": "One",
    })
    reg2 = await client.post("/api/auth/register", json={
        "email": "iso2@test.com", "password": "Test12345!", "first_name": "Iso", "last_name": "Two",
    })
    token1 = reg1.json()["access_token"]
    token2 = reg2.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}
    
    res = await client.post("/api/products", json={"name": "Private Product"}, headers=headers1)
    product_id = res.json()["id"]
    
    response = await client.get(f"/api/products/{product_id}", headers=headers2)
    assert response.status_code in [404, 302, 403]
