import pytest
from httpx import AsyncClient


async def _get_token(client: AsyncClient) -> str:
    reg = await client.post("/api/auth/register", json={
        "email": "drive@test.com",
        "password": "Test12345!",
        "first_name": "Drive",
        "last_name": "User",
    })
    return reg.json()["access_token"]


async def _create_product(client: AsyncClient, token: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Drive Test Product"}, headers=headers)
    return res.json()["id"]


async def _create_campaign(client: AsyncClient, token: str, product_id: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/campaigns", json={
        "name": "Drive Test Campaign",
        "product_id": product_id,
    }, headers=headers)
    return res.json()["id"]


@pytest.mark.asyncio
async def test_drive_status_not_connected(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/google-drive/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False


@pytest.mark.asyncio
async def test_drive_connect_mock(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/api/google-drive/connect-mock", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["google_email"] == "demo@gmail.com"


@pytest.mark.asyncio
async def test_drive_status_connected(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    response = await client.get("/api/google-drive/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["google_email"] == "demo@gmail.com"


@pytest.mark.asyncio
async def test_drive_browse_root(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    response = await client.get("/api/google-drive/browse/root", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert "folders" in data
    assert len(data["files"]) > 0


@pytest.mark.asyncio
async def test_drive_browse_specific_folder(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    response = await client.get("/api/google-drive/browse/mock_folder_001", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "mock_folder_001"


@pytest.mark.asyncio
async def test_drive_browse_not_connected(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/google-drive/browse/root", headers=headers)
    assert response.status_code == 400
    assert "not connected" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_drive_search(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    response = await client.get("/api/google-drive/search?q=product", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "files" in data


@pytest.mark.asyncio
async def test_drive_search_not_connected(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/google-drive/search?q=product", headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_drive_import_image(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    product_id = await _create_product(client, token)
    response = await client.post("/api/google-drive/import-image", json={
        "file_id": "mock_file_001",
        "product_id": product_id,
        "purpose": "HERO",
        "position": 0,
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["file_name"] == "product-photo-hero.jpg"
    assert data["status"] == "IMPORTED"
    assert data["image_url"] is not None


@pytest.mark.asyncio
async def test_drive_import_image_product_not_found(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    from uuid import uuid4
    response = await client.post("/api/google-drive/import-image", json={
        "file_id": "mock_file_001",
        "product_id": str(uuid4()),
        "purpose": "HERO",
    }, headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_drive_import_image_not_connected(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    product_id = await _create_product(client, token)
    response = await client.post("/api/google-drive/import-image", json={
        "file_id": "mock_file_001",
        "product_id": product_id,
        "purpose": "HERO",
    }, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_drive_import_document(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    product_id = await _create_product(client, token)
    response = await client.post("/api/google-drive/import-document", json={
        "file_id": "mock_file_004",
        "product_id": product_id,
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["external_file_name"] == "ad-copy-draft.txt"
    assert data["status"] == "READY"
    assert data["content_text"] is not None
    assert data["extracted_text"] is not None
    assert data["character_count"] > 0
    assert data["processed_at"] is not None


@pytest.mark.asyncio
async def test_drive_import_document_not_connected(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    product_id = await _create_product(client, token)
    response = await client.post("/api/google-drive/import-document", json={
        "file_id": "mock_file_004",
        "product_id": product_id,
    }, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_drive_import_asset(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    product_id = await _create_product(client, token)
    campaign_id = await _create_campaign(client, token, product_id)
    response = await client.post("/api/google-drive/import-asset", json={
        "file_id": "mock_file_002",
        "campaign_id": campaign_id,
        "purpose": "LIFESTYLE",
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["file_name"] == "lifestyle-shot-1.png"
    assert data["status"] == "IMPORTED"


@pytest.mark.asyncio
async def test_drive_import_asset_not_image(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    product_id = await _create_product(client, token)
    campaign_id = await _create_campaign(client, token, product_id)
    response = await client.post("/api/google-drive/import-asset", json={
        "file_id": "mock_file_004",
        "campaign_id": campaign_id,
    }, headers=headers)
    assert response.status_code == 400
    assert "images" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_drive_import_asset_campaign_not_found(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    from uuid import uuid4
    response = await client.post("/api/google-drive/import-asset", json={
        "file_id": "mock_file_001",
        "campaign_id": str(uuid4()),
    }, headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_drive_list_documents(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    product_id = await _create_product(client, token)
    await client.post("/api/google-drive/import-document", json={
        "file_id": "mock_file_004",
        "product_id": product_id,
    }, headers=headers)
    response = await client.get(f"/api/google-drive/documents/{product_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["external_file_name"] == "ad-copy-draft.txt"


@pytest.mark.asyncio
async def test_drive_list_documents_product_not_found(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    from uuid import uuid4
    response = await client.get(f"/api/google-drive/documents/{uuid4()}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_drive_disconnect(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    response = await client.post("/api/google-drive/disconnect", headers=headers)
    assert response.status_code == 200
    assert response.json()["disconnected"] is True
    status = await client.get("/api/google-drive/status", headers=headers)
    assert status.json()["connected"] is False


@pytest.mark.asyncio
async def test_drive_disconnect_not_connected(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post("/api/google-drive/disconnect", headers=headers)
    assert response.status_code == 200
    assert response.json()["disconnected"] is True


@pytest.mark.asyncio
async def test_drive_import_idempotent(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    product_id = await _create_product(client, token)
    res1 = await client.post("/api/google-drive/import-image", json={
        "file_id": "mock_file_001",
        "product_id": product_id,
        "purpose": "HERO",
    }, headers=headers)
    assert res1.status_code == 200
    product = await client.get(f"/api/products/{product_id}", headers=headers)
    image_count_before = len(product.json()["images"])
    res2 = await client.post("/api/google-drive/import-image", json={
        "file_id": "mock_file_001",
        "product_id": product_id,
        "purpose": "HERO",
    }, headers=headers)
    assert res2.status_code == 200
    product_after = await client.get(f"/api/products/{product_id}", headers=headers)
    assert len(product_after.json()["images"]) == image_count_before


@pytest.mark.asyncio
async def test_drive_connect_replaces_existing(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    res1 = await client.get("/api/google-drive/status", headers=headers)
    assert res1.json()["connected"] is True
    await client.post("/api/google-drive/connect-mock", headers=headers)
    res2 = await client.get("/api/google-drive/status", headers=headers)
    assert res2.json()["connected"] is True
    assert res2.json()["google_email"] == "demo@gmail.com"


@pytest.mark.asyncio
async def test_drive_import_document_product_not_found(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/api/google-drive/connect-mock", headers=headers)
    from uuid import uuid4
    response = await client.post("/api/google-drive/import-document", json={
        "file_id": "mock_file_004",
        "product_id": str(uuid4()),
    }, headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_drive_connect_get_auth_url(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/google-drive/connect", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "auth_url" in data
    assert "state" in data
