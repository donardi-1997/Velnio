import pytest
import uuid
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta


async def _setup(client: AsyncClient) -> tuple:
    reg = await client.post("/api/auth/register", json={
        "email": "tracking@test.com", "password": "Test12345!", "first_name": "Track", "last_name": "User",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post("/api/products", json={"name": "Track Product", "selling_price": 29.99}, headers=headers)
    product_id = res.json()["id"]
    camp = (await client.post(f"/api/campaigns/by-product/{product_id}", json={
        "name": "Track Campaign", "selling_price": 29.99
    }, headers=headers)).json()
    # Generate tracking key by updating campaign
    tracking_key = uuid.uuid4().hex[:32]
    await client.patch(f"/api/campaigns/{camp['id']}", json={"tracking_key": tracking_key}, headers=headers)
    return token, headers, camp["id"], tracking_key


@pytest.mark.asyncio
async def test_valid_page_view(client: AsyncClient):
    token, headers, campaign_id, tracking_key = await _setup(client)
    response = await client.post(f"/api/tracking/events/{tracking_key}", json={
        "event_type": "PAGE_VIEW",
        "session_id": str(uuid.uuid4()),
        "visitor_id": str(uuid.uuid4()),
        "source": "google",
        "medium": "cpc",
        "country": "US",
        "device_type": "desktop",
    })
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_invalid_event_type(client: AsyncClient):
    token, headers, campaign_id, tracking_key = await _setup(client)
    response = await client.post(f"/api/tracking/events/{tracking_key}", json={
        "event_type": "INVALID_TYPE",
        "session_id": str(uuid.uuid4()),
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_invalid_tracking_key(client: AsyncClient):
    response = await client.post("/api/tracking/events/nonexistent_key", json={
        "event_type": "PAGE_VIEW",
        "session_id": str(uuid.uuid4()),
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_revenue_validation(client: AsyncClient):
    token, headers, campaign_id, tracking_key = await _setup(client)
    response = await client.post(f"/api/tracking/events/{tracking_key}", json={
        "event_type": "PURCHASE",
        "session_id": str(uuid.uuid4()),
        "revenue": -10,
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_purchase_event(client: AsyncClient):
    token, headers, campaign_id, tracking_key = await _setup(client)
    response = await client.post(f"/api/tracking/events/{tracking_key}", json={
        "event_type": "PURCHASE",
        "session_id": str(uuid.uuid4()),
        "revenue": 49.99,
        "currency": "USD",
        "external_event_id": "shopify_order_123",
    })
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_purchase_deduplication(client: AsyncClient):
    token, headers, campaign_id, tracking_key = await _setup(client)
    event_id = "shopify_order_123"
    await client.post(f"/api/tracking/events/{tracking_key}", json={
        "event_type": "PURCHASE",
        "session_id": str(uuid.uuid4()),
        "revenue": 49.99,
        "external_event_id": event_id,
    })
    response = await client.post(f"/api/tracking/events/{tracking_key}", json={
        "event_type": "PURCHASE",
        "session_id": str(uuid.uuid4()),
        "revenue": 49.99,
        "external_event_id": event_id,
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_batch_events(client: AsyncClient):
    token, headers, campaign_id, tracking_key = await _setup(client)
    session_id = str(uuid.uuid4())
    visitor_id = str(uuid.uuid4())
    response = await client.post(f"/api/tracking/batch/{tracking_key}", json={
        "events": [
            {"event_type": "PAGE_VIEW", "session_id": session_id, "visitor_id": visitor_id},
            {"event_type": "CTA_CLICK", "session_id": session_id, "visitor_id": visitor_id},
            {"event_type": "ADD_TO_CART", "session_id": session_id, "visitor_id": visitor_id},
        ]
    })
    assert response.status_code == 200
    assert response.json()["events_accepted"] == 3
