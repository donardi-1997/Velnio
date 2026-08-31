import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_workspace_created_on_register(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "ws@test.com",
        "password": "Test12345!",
        "first_name": "WS",
        "last_name": "User",
    })
    token = reg.json()["access_token"]
    response = await client.get("/api/workspace", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "WS's Workspace"
