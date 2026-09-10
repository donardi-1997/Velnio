import httpx
import pytest
from httpx import AsyncClient

from app.core.exceptions import BadGatewayException
from app.services.google_drive.real_provider import RealGoogleDriveProvider


async def _get_token(client: AsyncClient) -> str:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "drive-hardening@test.com",
            "password": "Test12345!",
            "first_name": "Drive",
            "last_name": "Hardening",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_drive_oauth_state_is_single_use(client: AsyncClient):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    connect_response = await client.get("/api/google-drive/connect", headers=headers)
    assert connect_response.status_code == 200
    state = connect_response.json()["state"]

    first_callback = await client.get(
        "/api/google-drive/callback",
        params={"code": "mock_code", "state": state},
        follow_redirects=False,
    )
    assert first_callback.status_code in {302, 307}

    replay = await client.get(
        "/api/google-drive/callback",
        params={"code": "mock_code", "state": state},
        follow_redirects=False,
    )
    assert replay.status_code == 400
    assert "oauth state" in replay.json()["detail"].lower()


@pytest.mark.asyncio
async def test_drive_oauth_exchange_failure_does_not_leak_provider_error(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    token = await _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    connect_response = await client.get("/api/google-drive/connect", headers=headers)
    state = connect_response.json()["state"]

    class FailingProvider:
        async def exchange_code(self, code: str):
            raise RuntimeError("sensitive-provider-body client_secret=do-not-leak")

    monkeypatch.setattr(
        "app.modules.integrations.application.google_drive_connection.get_google_drive_provider",
        lambda: FailingProvider(),
    )

    callback = await client.get(
        "/api/google-drive/callback",
        params={"code": "bad_code", "state": state},
        follow_redirects=False,
    )

    assert callback.status_code == 400
    detail = callback.json()["detail"]
    assert detail == "Failed to authenticate with Google Drive; start the connection again"
    assert "client_secret" not in detail
    assert "do-not-leak" not in detail


@pytest.mark.asyncio
async def test_real_drive_provider_escapes_folder_query_literal(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict = {}

    class RecordingClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["request_kwargs"] = kwargs
            request = httpx.Request(method, url, params=kwargs.get("params"))
            return httpx.Response(200, request=request, json={"files": []})

    monkeypatch.setattr(
        "app.services.google_drive.real_provider.httpx.AsyncClient",
        RecordingClient,
    )

    provider = RealGoogleDriveProvider()
    await provider.list_files(
        "access-token",
        folder_id="folder'\\draft",
        query="name contains 'report'",
    )

    assert captured["client_kwargs"]["timeout"] == 15.0
    assert captured["request_kwargs"]["params"]["q"] == (
        "'folder\\'\\\\draft' in parents and trashed=false and name contains 'report'"
    )


@pytest.mark.asyncio
async def test_real_drive_provider_encodes_file_id_path_segment(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict = {}

    class RecordingClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, **kwargs):
            captured["url"] = url
            request = httpx.Request(method, url)
            return httpx.Response(
                200,
                request=request,
                json={"id": "id", "name": "name", "mimeType": "text/plain"},
            )

    monkeypatch.setattr(
        "app.services.google_drive.real_provider.httpx.AsyncClient",
        RecordingClient,
    )

    await RealGoogleDriveProvider().get_file("access-token", "file/with?reserved#chars")

    assert captured["url"].endswith("/files/file%2Fwith%3Freserved%23chars")


@pytest.mark.asyncio
async def test_real_drive_provider_timeout_maps_to_safe_502(
    monkeypatch: pytest.MonkeyPatch,
):
    class TimeoutClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, **kwargs):
            request = httpx.Request(method, url)
            raise httpx.ConnectTimeout(
                "sensitive-network-details token=do-not-leak",
                request=request,
            )

    monkeypatch.setattr(
        "app.services.google_drive.real_provider.httpx.AsyncClient",
        TimeoutClient,
    )

    with pytest.raises(BadGatewayException) as exc_info:
        await RealGoogleDriveProvider().list_files("super-secret-token")

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Google Drive request timed out; try again"
    assert "super-secret-token" not in exc_info.value.detail
    assert "do-not-leak" not in exc_info.value.detail


@pytest.mark.asyncio
async def test_real_drive_provider_http_error_maps_to_safe_502(
    monkeypatch: pytest.MonkeyPatch,
):
    class ErrorClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, **kwargs):
            request = httpx.Request(method, url)
            return httpx.Response(
                503,
                request=request,
                text="sensitive-google-response refresh_token=do-not-leak",
            )

    monkeypatch.setattr(
        "app.services.google_drive.real_provider.httpx.AsyncClient",
        ErrorClient,
    )

    with pytest.raises(BadGatewayException) as exc_info:
        await RealGoogleDriveProvider().refresh_token("super-secret-refresh-token")

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Google Drive request failed; try again"
    assert "refresh_token" not in exc_info.value.detail
    assert "do-not-leak" not in exc_info.value.detail


@pytest.mark.asyncio
async def test_real_drive_provider_invalid_json_maps_to_safe_502(
    monkeypatch: pytest.MonkeyPatch,
):
    class InvalidJsonClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, **kwargs):
            request = httpx.Request(method, url)
            return httpx.Response(200, request=request, content=b"not-json")

    monkeypatch.setattr(
        "app.services.google_drive.real_provider.httpx.AsyncClient",
        InvalidJsonClient,
    )

    with pytest.raises(BadGatewayException) as exc_info:
        await RealGoogleDriveProvider().list_files("access-token")

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Google Drive returned an invalid response"
