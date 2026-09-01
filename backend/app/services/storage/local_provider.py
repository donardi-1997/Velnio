import os
import uuid
import hashlib
import aiofiles
from typing import Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LocalStorageProvider:
    def __init__(self):
        self.base_path = settings.LOCAL_STORAGE_PATH
        os.makedirs(self.base_path, exist_ok=True)

    async def save_bytes(self, data: bytes, content_type: str, directory: str = "uploads") -> str:
        ext = self._ext_from_content_type(content_type)
        key = f"{directory}/{uuid.uuid4().hex}{ext}"
        full_path = os.path.join(self.base_path, key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(data)
        return key

    async def save_from_url(self, url: str, directory: str = "imports") -> str:
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "image/jpeg")
            return await self.save_bytes(response.content, content_type, directory)

    async def read_bytes(self, key: str) -> bytes:
        full_path = os.path.join(self.base_path, key)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Storage key not found: {key}")
        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def delete(self, key: str) -> None:
        full_path = os.path.join(self.base_path, key)
        if os.path.exists(full_path):
            os.remove(full_path)

    def get_public_url(self, key: str) -> str:
        return f"/storage/{key}"

    def _ext_from_content_type(self, content_type: str) -> str:
        mapping = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
        return mapping.get(content_type.split(";")[0].strip(), ".bin")
