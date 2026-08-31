from typing import Optional


class S3StorageProvider:
    """Placeholder for S3 storage provider. Implement when S3 integration is needed."""

    def __init__(self):
        raise NotImplementedError("S3 storage provider is not yet implemented.")

    async def save_bytes(self, data: bytes, content_type: str, directory: str = "uploads") -> str:
        raise NotImplementedError

    async def save_from_url(self, url: str, directory: str = "imports") -> str:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    def get_public_url(self, key: str) -> str:
        raise NotImplementedError
