import io
import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "images@test.com", "password": "Test12345!", "first_name": "Images", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Image Product", "selling_price": 29.99}, headers=headers)
    return token, headers, res.json()["id"]


@pytest.mark.asyncio
async def test_upload_valid_image(client: AsyncClient):
    token, headers, product_id = await _setup(client)
    # Create a minimal valid PNG
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02'
        b'\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01'
        b'\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    files = {"files": ("test.png", io.BytesIO(png_data), "image/png")}
    response = await client.post(f"/api/products/{product_id}/images/upload", files=files, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["images"]) >= 1


@pytest.mark.asyncio
async def test_reject_invalid_mime(client: AsyncClient):
    token, headers, product_id = await _setup(client)
    files = {"files": ("test.txt", io.BytesIO(b"not an image"), "text/plain")}
    response = await client.post(f"/api/products/{product_id}/images/upload", files=files, headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_mock_generation(client: AsyncClient):
    token, headers, product_id = await _setup(client)
    # Create a campaign first
    camp = (await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Image Test Campaign",
    }, headers=headers)).json()

    # Generate visual direction
    vd_resp = await client.post(f"/api/campaigns/{camp['id']}/visual-direction/generate", headers=headers)
    assert vd_resp.status_code == 200

    # Generate launch pack
    response = await client.post(f"/api/campaigns/{camp['id']}/assets/generate", json={
        "preset": "launch_pack"
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generated"
    assert data["count"] > 0


@pytest.mark.asyncio
async def test_select_asset(client: AsyncClient):
    token, headers, product_id = await _setup(client)
    camp = (await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Select Asset Campaign",
    }, headers=headers)).json()

    await client.post(f"/api/campaigns/{camp['id']}/visual-direction/generate", headers=headers)
    gen = (await client.post(f"/api/campaigns/{camp['id']}/assets/generate", json={
        "preset": "launch_pack"
    }, headers=headers)).json()

    if gen["count"] > 0:
        image_id = gen["images"][0]["id"]
        response = await client.post(f"/api/campaigns/{camp['id']}/assets/{image_id}/select?purpose=HERO", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "selected"


@pytest.mark.asyncio
async def test_launch_pack_consumes_credits(client: AsyncClient):
    token, headers, product_id = await _setup(client)
    camp = (await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Credit Test Campaign",
    }, headers=headers)).json()

    await client.post(f"/api/campaigns/{camp['id']}/visual-direction/generate", headers=headers)
    wallet_before = (await client.get("/api/credits", headers=headers)).json()["balance"]
    await client.post(f"/api/campaigns/{camp['id']}/assets/generate", json={"preset": "launch_pack"}, headers=headers)
    wallet_after = (await client.get("/api/credits", headers=headers)).json()["balance"]
    assert wallet_after < wallet_before
