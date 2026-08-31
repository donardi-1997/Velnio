from typing import Optional, Dict, Any, List
import json
from app.services.google_drive.base import GoogleDriveProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


class MockGoogleDriveProvider(GoogleDriveProvider):
    DEMO_FILES = [
        {
            "id": "mock_file_001",
            "name": "product-photo-hero.jpg",
            "mimeType": "image/jpeg",
            "size": 245760,
            "createdTime": "2025-01-15T10:00:00Z",
            "modifiedTime": "2025-01-15T10:00:00Z",
            "thumbnailLink": None,
            "webViewLink": None,
        },
        {
            "id": "mock_file_002",
            "name": "lifestyle-shot-1.png",
            "mimeType": "image/png",
            "size": 512000,
            "createdTime": "2025-01-16T12:00:00Z",
            "modifiedTime": "2025-01-16T12:00:00Z",
            "thumbnailLink": None,
            "webViewLink": None,
        },
        {
            "id": "mock_file_003",
            "name": "product-description.pdf",
            "mimeType": "application/pdf",
            "size": 102400,
            "createdTime": "2025-01-17T14:00:00Z",
            "modifiedTime": "2025-01-17T14:00:00Z",
            "thumbnailLink": None,
            "webViewLink": None,
        },
        {
            "id": "mock_file_004",
            "name": "ad-copy-draft.txt",
            "mimeType": "text/plain",
            "size": 2048,
            "createdTime": "2025-01-18T09:00:00Z",
            "modifiedTime": "2025-01-18T09:00:00Z",
            "thumbnailLink": None,
            "webViewLink": None,
        },
        {
            "id": "mock_file_005",
            "name": "campaign-brief.docx",
            "mimeType": "application/vnd.google-apps.document",
            "size": None,
            "createdTime": "2025-01-19T11:00:00Z",
            "modifiedTime": "2025-01-19T11:00:00Z",
            "thumbnailLink": None,
            "webViewLink": None,
        },
    ]

    DEMO_FOLDERS = [
        {
            "id": "mock_folder_001",
            "name": "Campaign Assets",
            "mimeType": "application/vnd.google-apps.folder",
            "size": None,
            "createdTime": "2025-01-10T08:00:00Z",
            "modifiedTime": "2025-01-10T08:00:00Z",
        },
        {
            "id": "mock_folder_002",
            "name": "Product Photos",
            "mimeType": "application/vnd.google-apps.folder",
            "size": None,
            "createdTime": "2025-01-11T09:00:00Z",
            "modifiedTime": "2025-01-11T09:00:00Z",
        },
    ]

    async def get_auth_url(self, state: str) -> str:
        return f"https://accounts.google.com/o/oauth2/v2/auth?mock=true&state={state}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        return {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/drive.file",
            "token_type": "Bearer",
        }

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        return {
            "access_token": "mock_access_token_refreshed",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    async def list_files(
        self,
        access_token: str,
        folder_id: str = "root",
        page_size: int = 50,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        all_items = list(self.DEMO_FOLDERS) + list(self.DEMO_FILES)
        return {
            "files": all_items,
            "nextPageToken": None,
        }

    async def get_file(self, access_token: str, file_id: str) -> Dict[str, Any]:
        for f in self.DEMO_FILES + self.DEMO_FOLDERS:
            if f["id"] == file_id:
                return f
        return {"id": file_id, "name": "unknown", "mimeType": "application/octet-stream"}

    async def download_file(self, access_token: str, file_id: str) -> bytes:
        return b"mock file content"

    async def export_file(self, access_token: str, file_id: str, mime_type: str) -> bytes:
        return b"mock exported content"
