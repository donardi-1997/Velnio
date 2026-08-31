from typing import Optional, Dict, Any
import httpx
from app.services.google_drive.base import GoogleDriveProvider
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_API = "https://www.googleapis.com/drive/v3"
GOOGLE_DRIVE_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"


class RealGoogleDriveProvider(GoogleDriveProvider):
    def _get_client_id(self) -> str:
        return settings.GOOGLE_DRIVE_CLIENT_ID

    def _get_client_secret(self) -> str:
        return settings.GOOGLE_DRIVE_CLIENT_SECRET

    def _get_redirect_uri(self) -> str:
        return settings.GOOGLE_DRIVE_REDIRECT_URI

    def _get_scopes(self) -> str:
        return settings.GOOGLE_DRIVE_SCOPES

    def _get_headers(self, access_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def get_auth_url(self, state: str) -> str:
        scopes = self._get_scopes()
        params = {
            "client_id": self._get_client_id(),
            "redirect_uri": self._get_redirect_uri(),
            "response_type": "code",
            "scope": scopes,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GOOGLE_AUTH_URL}?{query}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._get_client_id(),
                    "client_secret": self._get_client_secret(),
                    "redirect_uri": self._get_redirect_uri(),
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            data = response.json()
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", ""),
                "expires_in": data.get("expires_in", 3600),
                "scope": data.get("scope", self._get_scopes()),
                "token_type": data.get("token_type", "Bearer"),
            }

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self._get_client_id(),
                    "client_secret": self._get_client_secret(),
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            response.raise_for_status()
            data = response.json()
            return {
                "access_token": data["access_token"],
                "expires_in": data.get("expires_in", 3600),
                "token_type": data.get("token_type", "Bearer"),
            }

    async def list_files(
        self,
        access_token: str,
        folder_id: str = "root",
        page_size: int = 50,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = {
            "q": f"'{folder_id}' in parents and trashed=false" if not query else f"'{folder_id}' in parents and trashed=false and {query}",
            "pageSize": str(page_size),
            "fields": "nextPageToken, files(id, name, mimeType, size, thumbnailLink, createdTime, modifiedTime, webViewLink)",
            "orderBy": "name",
        }
        if page_token:
            params["pageToken"] = page_token

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GOOGLE_DRIVE_API}/files",
                headers=self._get_headers(access_token),
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def get_file(self, access_token: str, file_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GOOGLE_DRIVE_API}/files/{file_id}",
                headers=self._get_headers(access_token),
                params={"fields": "id, name, mimeType, size, thumbnailLink, createdTime, modifiedTime, webViewLink"},
            )
            response.raise_for_status()
            return response.json()

    async def download_file(self, access_token: str, file_id: str) -> bytes:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GOOGLE_DRIVE_API}/files/{file_id}",
                headers=self._get_headers(access_token),
                params={"alt": "media"},
            )
            response.raise_for_status()
            return response.content

    async def export_file(self, access_token: str, file_id: str, mime_type: str) -> bytes:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GOOGLE_DRIVE_API}/files/{file_id}/export",
                headers=self._get_headers(access_token),
                params={"mimeType": mime_type},
            )
            response.raise_for_status()
            return response.content
