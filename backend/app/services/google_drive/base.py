from typing import Optional, Dict, Any, List


class GoogleDriveProvider:
    async def get_auth_url(self, state: str) -> str:
        raise NotImplementedError

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def list_files(
        self,
        access_token: str,
        folder_id: str = "root",
        page_size: int = 50,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def get_file(self, access_token: str, file_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def download_file(self, access_token: str, file_id: str) -> bytes:
        raise NotImplementedError

    async def export_file(self, access_token: str, file_id: str, mime_type: str) -> bytes:
        raise NotImplementedError
