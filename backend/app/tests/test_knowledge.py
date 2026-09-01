import pytest
from httpx import AsyncClient
from uuid import uuid4


async def _get_token(client: AsyncClient) -> str:
    await client.post("/api/auth/register", json={"email": "test@example.com", "password": "testpass123", "first_name": "Test", "last_name": "User"})
    response = await client.post("/api/auth/login", json={"email": "test@example.com", "password": "testpass123"})
    return response.json()["access_token"]


async def _create_product(client: AsyncClient, token: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/api/products", json={
        "name": "Test Product",
        "source_type": "MANUAL",
        "target_country": "US",
        "target_language": "en",
        "currency": "USD",
    }, headers=headers)
    return response.json()["id"]


@pytest.mark.asyncio
async def test_list_knowledge_empty(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/knowledge/", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_knowledge_source(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    product_id = await _create_product(client, token)
    response = await client.post("/api/knowledge/", json={
        "product_id": product_id,
        "source_type": "MANUAL",
        "content_type": "TEXT",
        "title": "Test Knowledge",
        "content_text": "This is test knowledge content",
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Knowledge"
    assert data["source_type"] == "MANUAL"
    assert data["status"] == "ACTIVE"
    assert data["content_hash"] is not None


@pytest.mark.asyncio
async def test_create_knowledge_no_entity(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/api/knowledge/", json={
        "source_type": "MANUAL",
        "content_type": "TEXT",
        "title": "Test",
    }, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_knowledge_source(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    product_id = await _create_product(client, token)
    create_res = await client.post("/api/knowledge/", json={
        "product_id": product_id,
        "source_type": "REVIEWS",
        "content_type": "TEXT",
        "title": "Customer Reviews",
        "content_text": "Great product!",
    }, headers=headers)
    source_id = create_res.json()["id"]
    response = await client.get(f"/api/knowledge/{source_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Customer Reviews"


@pytest.mark.asyncio
async def test_update_knowledge_source(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    product_id = await _create_product(client, token)
    create_res = await client.post("/api/knowledge/", json={
        "product_id": product_id,
        "source_type": "MANUAL",
        "content_type": "TEXT",
        "title": "Original Title",
        "content_text": "Original content",
    }, headers=headers)
    source_id = create_res.json()["id"]
    response = await client.patch(f"/api/knowledge/{source_id}", json={
        "title": "Updated Title",
        "is_primary": True,
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["is_primary"] is True


@pytest.mark.asyncio
async def test_delete_knowledge_source(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    product_id = await _create_product(client, token)
    create_res = await client.post("/api/knowledge/", json={
        "product_id": product_id,
        "source_type": "MANUAL",
        "content_type": "TEXT",
        "title": "To Delete",
    }, headers=headers)
    source_id = create_res.json()["id"]
    response = await client.delete(f"/api/knowledge/{source_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["deleted"] is True


@pytest.mark.asyncio
async def test_knowledge_source_limit(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    product_id = await _create_product(client, token)
    for i in range(20):
        await client.post("/api/knowledge/", json={
            "product_id": product_id,
            "source_type": "MANUAL",
            "content_type": "TEXT",
            "title": f"Source {i}",
        }, headers=headers)
    response = await client.post("/api/knowledge/", json={
        "product_id": product_id,
        "source_type": "MANUAL",
        "content_type": "TEXT",
        "title": "Source 21",
    }, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_knowledge_with_filter(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    product_id = await _create_product(client, token)
    await client.post("/api/knowledge/", json={
        "product_id": product_id,
        "source_type": "MANUAL",
        "content_type": "TEXT",
        "title": "Manual Source",
    }, headers=headers)
    await client.post("/api/knowledge/", json={
        "product_id": product_id,
        "source_type": "REVIEWS",
        "content_type": "TEXT",
        "title": "Review Source",
    }, headers=headers)
    response = await client.get("/api/knowledge/?source_type=MANUAL", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source_type"] == "MANUAL"
