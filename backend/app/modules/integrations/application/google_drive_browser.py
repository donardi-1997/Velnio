from uuid import UUID

from app.schemas.google_drive import GoogleDriveFile, GoogleDriveFolder, GoogleDriveSearchResult
from app.services.google_drive import get_google_drive_provider
from app.modules.integrations.application.google_drive_connection import GoogleDriveConnectionService


class GoogleDriveBrowserService:
    def __init__(self, connection_service: GoogleDriveConnectionService) -> None:
        self.connection_service = connection_service

    @staticmethod
    def _is_folder(mime_type: str) -> bool:
        return mime_type == "application/vnd.google-apps.folder"

    @staticmethod
    def _escape_query_literal(value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

    def _format_file(self, file_data: dict) -> GoogleDriveFile:
        return GoogleDriveFile(
            id=file_data["id"],
            name=file_data["name"],
            mime_type=file_data["mimeType"],
            size=file_data.get("size"),
            thumbnail_url=file_data.get("thumbnailLink"),
            created_time=file_data.get("createdTime"),
            modified_time=file_data.get("modifiedTime"),
            web_view_link=file_data.get("webViewLink"),
            is_folder=self._is_folder(file_data["mimeType"]),
        )

    async def browse(
        self,
        workspace_id: UUID,
        folder_id: str,
        page_size: int,
        page_token: str | None,
    ) -> GoogleDriveFolder:
        access_token = await self.connection_service.get_valid_token(workspace_id)
        provider = get_google_drive_provider()
        data = await provider.list_files(
            access_token=access_token,
            folder_id=folder_id,
            page_size=page_size,
            page_token=page_token,
        )
        files = [self._format_file(item) for item in data.get("files", [])]
        return GoogleDriveFolder(
            id=folder_id,
            name="Root" if folder_id == "root" else folder_id,
            files=[item for item in files if not item.is_folder],
            folders=[item for item in files if item.is_folder],
        )

    async def search(
        self,
        workspace_id: UUID,
        query: str,
        page_size: int,
        page_token: str | None,
    ) -> GoogleDriveSearchResult:
        access_token = await self.connection_service.get_valid_token(workspace_id)
        provider = get_google_drive_provider()
        escaped_query = self._escape_query_literal(query)
        search_query = f"name contains '{escaped_query}'"
        data = await provider.list_files(
            access_token=access_token,
            folder_id="root",
            page_size=page_size,
            page_token=page_token,
            query=search_query,
        )
        return GoogleDriveSearchResult(
            files=[self._format_file(item) for item in data.get("files", [])],
            next_page_token=data.get("nextPageToken"),
        )
