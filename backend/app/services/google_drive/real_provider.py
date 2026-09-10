from typing import Optional, Dict, Any
from urllib.parse import quote, urlencode

import httpx

from app.core.config import settings
from app.core.exceptions import BadGatewayException
from app.core.logging import get_logger
from app.services.google_drive.base import GoogleDriveProvider

logger = get_logger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_API = "https://www.googleapis.com/drive/v3"
GOOGLE_DRIVE_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
GOOGLE_DRIVE_TIMEOUT_SECONDS = 15.0


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

    @staticmethod
    def _escape_query_literal(value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

    @staticmethod
    def _encode_path_segment(value: str) -> str:
        return quote(value, safe="")

    async def _request(
        self,
        method: str,
        url: str,
        *,
        operation: str,
        **kwargs,
    ) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=GOOGLE_DRIVE_TIMEOUT_SECONDS) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
        except httpx.TimeoutException as exc:
            logger.warning("Google Drive %s timed out", operation)
            raise BadGatewayException("Google Drive request timed out; try again") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Google Drive %s failed with HTTP %s",
                operation,
                exc.response.status_code,
            )
            raise BadGatewayException("Google Drive request failed; try again") from exc
        except httpx.RequestError as exc:
            logger.warning("Google Drive %s failed with a network error", operation)
            raise BadGatewayException("Google Drive request failed; try again") from exc

    @staticmethod
    def _json_response(response: httpx.Response, operation: str) -> Dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            logger.warning("Google Drive %s returned invalid JSON", operation)
            raise BadGatewayException("Google Drive returned an invalid response") from exc
        if not isinstance(data, dict):
            logger.warning("Google Drive %s returned a non-object JSON payload", operation)
            raise BadGatewayException("Google Drive returned an invalid response")
        return data

    @staticmethod
    def _require_access_token(data: Dict[str, Any], operation: str) -> str:
        access_token = data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            logger.warning("Google Drive %s response omitted access_token", operation)
            raise BadGatewayException("Google Drive returned an invalid token response")
        return access_token

    async def get_auth_url(self, state: str) -> str:
        params = {
            "client_id": self._get_client_id(),
            "redirect_uri": self._get_redirect_uri(),
            "response_type": "code",
            "scope": self._get_scopes(),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        response = await self._request(
            "POST",
            GOOGLE_TOKEN_URL,
            operation="OAuth code exchange",
            data={
                "code": code,
                "client_id": self._get_client_id(),
                "client_secret": self._get_client_secret(),
                "redirect_uri": self._get_redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        data = self._json_response(response, "OAuth code exchange")
        access_token = self._require_access_token(data, "OAuth code exchange")
        return {
            "access_token": access_token,
            "refresh_token": data.get("refresh_token", ""),
            "expires_in": data.get("expires_in", 3600),
            "scope": data.get("scope", self._get_scopes()),
            "token_type": data.get("token_type", "Bearer"),
        }

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        response = await self._request(
            "POST",
            GOOGLE_TOKEN_URL,
            operation="token refresh",
            data={
                "client_id": self._get_client_id(),
                "client_secret": self._get_client_secret(),
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        data = self._json_response(response, "token refresh")
        access_token = self._require_access_token(data, "token refresh")
        return {
            "access_token": access_token,
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
        escaped_folder_id = self._escape_query_literal(folder_id)
        parent_query = f"'{escaped_folder_id}' in parents and trashed=false"
        params = {
            "q": parent_query if not query else f"{parent_query} and {query}",
            "pageSize": str(page_size),
            "fields": "nextPageToken, files(id, name, mimeType, size, thumbnailLink, createdTime, modifiedTime, webViewLink)",
            "orderBy": "name",
        }
        if page_token:
            params["pageToken"] = page_token

        response = await self._request(
            "GET",
            f"{GOOGLE_DRIVE_API}/files",
            operation="file listing",
            headers=self._get_headers(access_token),
            params=params,
        )
        return self._json_response(response, "file listing")

    async def get_file(self, access_token: str, file_id: str) -> Dict[str, Any]:
        encoded_file_id = self._encode_path_segment(file_id)
        response = await self._request(
            "GET",
            f"{GOOGLE_DRIVE_API}/files/{encoded_file_id}",
            operation="file metadata lookup",
            headers=self._get_headers(access_token),
            params={"fields": "id, name, mimeType, size, thumbnailLink, createdTime, modifiedTime, webViewLink"},
        )
        return self._json_response(response, "file metadata lookup")

    async def download_file(self, access_token: str, file_id: str) -> bytes:
        encoded_file_id = self._encode_path_segment(file_id)
        response = await self._request(
            "GET",
            f"{GOOGLE_DRIVE_API}/files/{encoded_file_id}",
            operation="file download",
            headers=self._get_headers(access_token),
            params={"alt": "media"},
        )
        return response.content

    async def export_file(self, access_token: str, file_id: str, mime_type: str) -> bytes:
        encoded_file_id = self._encode_path_segment(file_id)
        response = await self._request(
            "GET",
            f"{GOOGLE_DRIVE_API}/files/{encoded_file_id}/export",
            operation="file export",
            headers=self._get_headers(access_token),
            params={"mimeType": mime_type},
        )
        return response.content
