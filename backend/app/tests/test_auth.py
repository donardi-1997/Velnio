import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post("/api/auth/register", json={
        "email": "test@test.com",
        "password": "Test12345!",
        "first_name": "Test",
        "last_name": "User",
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "login@test.com",
        "password": "Test12345!",
        "first_name": "Login",
        "last_name": "User",
    })
    response = await client.post("/api/auth/login", json={
        "email": "login@test.com",
        "password": "Test12345!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_me(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "me@test.com",
        "password": "Test12345!",
        "first_name": "Me",
        "last_name": "User",
    })
    token = reg.json()["access_token"]
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@test.com"


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "refresh@test.com",
        "password": "Test12345!",
        "first_name": "Refresh",
        "last_name": "User",
    })
    refresh = reg.json()["refresh_token"]
    response = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    assert "access_token" in response.json()
