import io

import pytest
from httpx import AsyncClient

from app.core.config import settings


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "images@test.com", "password": "Test12345!", "first_name": "Images", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Image Product", "selling_price": 29.99}, headers=headers)
    return token, headers, res.json()["id"]


async def _create_campaign(client: AsyncClient, headers: dict, product_id: str, name: str) -> dict:
    response = await client.post(
        f"/api/campaigns/by-product/{product_id}",
        json={"name": name},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_upload_valid_image(client: AsyncClient):
    token, headers, product_id = await _setup(client)
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
    camp = await _create_campaign(client, headers, product_id, "Image Test Campaign")

    vd_resp = await client.post(f"/api/campaigns/{camp['id']}/visual-direction/generate", headers=headers)
    assert vd_resp.status_code == 200

    response = await client.post(f"/api/campaigns/{camp['id']}/assets/generate", json={
        "preset": "launch_pack"
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generated"
    assert data["count"] > 0
    assert data["failed_count"] == 0
    assert data["credits_charged"] == settings.PLAN_LAUNCH_PACK_COST


@pytest.mark.asyncio
async def test_select_asset(client: AsyncClient):
    token, headers, product_id = await _setup(client)
    camp = await _create_campaign(client, headers, product_id, "Select Asset Campaign")

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
    camp = await _create_campaign(client, headers, product_id, "Credit Test Campaign")

    wallet_before = (await client.get("/api/credits", headers=headers)).json()["balance"]
    response = await client.post(
        f"/api/campaigns/{camp['id']}/assets/generate",
        json={"preset": "launch_pack"},
        headers=headers,
    )
    wallet_after = (await client.get("/api/credits", headers=headers)).json()["balance"]
    assert response.status_code == 200
    assert wallet_after == wallet_before - settings.PLAN_LAUNCH_PACK_COST


@pytest.mark.asyncio
async def test_regenerate_asset_creates_unselected_candidate_and_consumes_exact_cost(client: AsyncClient):
    token, headers, product_id = await _setup(client)
    camp = await _create_campaign(client, headers, product_id, "Regeneration Campaign")
    launch = (
        await client.post(
            f"/api/campaigns/{camp['id']}/assets/generate",
            json={"preset": "launch_pack"},
            headers=headers,
        )
    ).json()
    source = launch["images"][0]
    wallet_before = (await client.get("/api/credits", headers=headers)).json()["balance"]

    response = await client.post(
        f"/api/campaigns/{camp['id']}/assets/{source['id']}/regenerate",
        json={"instructions": "Use a brighter lifestyle composition"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "regenerated"
    assert data["source_image_id"] == source["id"]
    assert data["image"]["id"] != source["id"]
    assert data["image"]["purpose"] == source["purpose"]
    assert data["image"]["selected"] is False
    assert data["credits_charged"] == settings.PLAN_IMAGE_COST
    wallet_after = (await client.get("/api/credits", headers=headers)).json()["balance"]
    assert wallet_after == wallet_before - settings.PLAN_IMAGE_COST


@pytest.mark.asyncio
async def test_regenerate_asset_is_scoped_to_campaign(client: AsyncClient):
    token, headers, product_id = await _setup(client)
    source_campaign = await _create_campaign(client, headers, product_id, "Source Campaign")
    other_campaign = await _create_campaign(client, headers, product_id, "Other Campaign")
    launch = (
        await client.post(
            f"/api/campaigns/{source_campaign['id']}/assets/generate",
            json={"preset": "launch_pack"},
            headers=headers,
        )
    ).json()
    image_id = launch["images"][0]["id"]

    response = await client.post(
        f"/api/campaigns/{other_campaign['id']}/assets/{image_id}/regenerate",
        json={},
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_regeneration_provider_failure_does_not_consume_credits(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    token, headers, product_id = await _setup(client)
    camp = await _create_campaign(client, headers, product_id, "Provider Failure Campaign")
    launch = (
        await client.post(
            f"/api/campaigns/{camp['id']}/assets/generate",
            json={"preset": "launch_pack"},
            headers=headers,
        )
    ).json()
    image_id = launch["images"][0]["id"]
    wallet_before = (await client.get("/api/credits", headers=headers)).json()["balance"]

    class FailingProvider:
        async def generate_campaign_asset(self, *args, **kwargs):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "app.modules.campaigns.application.visual_assets.get_image_provider",
        lambda: FailingProvider(),
    )

    response = await client.post(
        f"/api/campaigns/{camp['id']}/assets/{image_id}/regenerate",
        json={},
        headers=headers,
    )

    assert response.status_code == 400
    wallet_after = (await client.get("/api/credits", headers=headers)).json()["balance"]
    assert wallet_after == wallet_before


@pytest.mark.asyncio
async def test_partial_launch_pack_charges_only_for_successful_assets(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    token, headers, product_id = await _setup(client)
    camp = await _create_campaign(client, headers, product_id, "Partial Pack Campaign")
    wallet_before = (await client.get("/api/credits", headers=headers)).json()["balance"]

    class PartialProvider:
        def __init__(self):
            self.calls = 0

        async def generate_campaign_asset(self, *args, **kwargs):
            self.calls += 1
            if self.calls > 3:
                raise RuntimeError("simulated partial outage")
            purpose = args[-1]
            return {
                "image_url": f"/storage/mock/partial-{self.calls}-{purpose}.png",
                "width": 1200,
                "height": 628,
            }

    provider = PartialProvider()
    monkeypatch.setattr(
        "app.modules.campaigns.application.visual_assets.get_image_provider",
        lambda: provider,
    )

    response = await client.post(
        f"/api/campaigns/{camp['id']}/assets/generate",
        json={"preset": "launch_pack"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "partially_generated"
    assert data["count"] == 3
    assert data["failed_count"] == 5
    expected_charge = (3 * settings.PLAN_LAUNCH_PACK_COST + 7) // 8
    assert data["credits_charged"] == expected_charge
    wallet_after = (await client.get("/api/credits", headers=headers)).json()["balance"]
    assert wallet_after == wallet_before - expected_charge


@pytest.mark.asyncio
async def test_launch_pack_total_provider_failure_does_not_consume_credits(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    token, headers, product_id = await _setup(client)
    camp = await _create_campaign(client, headers, product_id, "Failed Pack Campaign")
    wallet_before = (await client.get("/api/credits", headers=headers)).json()["balance"]

    class FailingProvider:
        async def generate_campaign_asset(self, *args, **kwargs):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "app.modules.campaigns.application.visual_assets.get_image_provider",
        lambda: FailingProvider(),
    )

    response = await client.post(
        f"/api/campaigns/{camp['id']}/assets/generate",
        json={"preset": "launch_pack"},
        headers=headers,
    )

    assert response.status_code == 400
    wallet_after = (await client.get("/api/credits", headers=headers)).json()["balance"]
    assert wallet_after == wallet_before
