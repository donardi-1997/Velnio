import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "import@test.com", "password": "Test12345!", "first_name": "Import", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return token, headers


@pytest.mark.asyncio
async def test_import_preview(client: AsyncClient):
    token, headers = await _setup(client)
    response = await client.post("/api/products/import/preview", json={
        "url": "https://example.com/product/test"
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "source_url" in data


@pytest.mark.asyncio
async def test_import_create_product(client: AsyncClient):
    token, headers = await _setup(client)
    preview = (await client.post("/api/products/import/preview", json={
        "url": "https://example.com/product/test"
    }, headers=headers)).json()

    response = await client.post("/api/products/import/create", json={
        "name": preview["name"] or "Imported Product",
        "description": preview.get("description", ""),
        "selling_price": preview.get("price", 29.99),
        "currency": preview.get("currency", "USD"),
        "source_url": preview["source_url"],
        "source_type": "OTHER",
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"]


@pytest.mark.asyncio
async def test_invalid_url_import(client: AsyncClient):
    token, headers = await _setup(client)
    response = await client.post("/api/products/import/preview", json={
        "url": "not-a-valid-url"
    }, headers=headers)
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_localhost_ssrf_blocked(client: AsyncClient):
    token, headers = await _setup(client)
    response = await client.post("/api/products/import/preview", json={
        "url": "http://localhost:8080/admin"
    }, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_private_ip_ssrf_blocked(client: AsyncClient):
    token, headers = await _setup(client)
    response = await client.post("/api/products/import/preview", json={
        "url": "http://192.168.1.1/admin"
    }, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_metadata_ip_ssrf_blocked(client: AsyncClient):
    token, headers = await _setup(client)
    response = await client.post("/api/products/import/preview", json={
        "url": "http://169.254.169.254/latest/meta-data/"
    }, headers=headers)
    assert response.status_code == 400
