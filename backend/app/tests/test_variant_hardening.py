import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "variant-hardening@test.com",
            "password": "Test12345!",
            "first_name": "Variant",
            "last_name": "Hardening",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_product_and_campaign(client: AsyncClient, headers: dict, suffix: str):
    product_response = await client.post(
        "/api/products",
        json={"name": f"Hardening Product {suffix}", "selling_price": 29.99},
        headers=headers,
    )
    assert product_response.status_code == 201
    product_id = product_response.json()["id"]

    campaign_response = await client.post(
        f"/api/campaigns/by-product/{product_id}",
        json={"name": f"Hardening Campaign {suffix}", "selling_price": 29.99},
        headers=headers,
    )
    assert campaign_response.status_code == 201
    return product_id, campaign_response.json()["id"]


@pytest.mark.asyncio
async def test_clone_variant_rejects_source_from_another_campaign(client: AsyncClient):
    headers = await _register(client)
    _, first_campaign_id = await _create_product_and_campaign(client, headers, "A")
    _, second_campaign_id = await _create_product_and_campaign(client, headers, "B")

    source_response = await client.post(
        f"/api/campaigns/{second_campaign_id}/variants",
        json={"name": "Other Campaign Variant"},
        headers=headers,
    )
    assert source_response.status_code == 201
    source_variant_id = source_response.json()["id"]

    clone_response = await client.post(
        f"/api/campaigns/{first_campaign_id}/variants",
        json={
            "name": "Invalid Clone",
            "clone_from_variant_id": source_variant_id,
        },
        headers=headers,
    )

    assert clone_response.status_code == 404
    assert "source variant" in clone_response.json()["detail"].lower()
