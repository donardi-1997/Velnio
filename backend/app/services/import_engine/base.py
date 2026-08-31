from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ProductSourceProvider(ABC):
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this provider can handle the given URL."""
        raise NotImplementedError

    @abstractmethod
    def normalize_url(self, url: str) -> str:
        """Normalize the URL for consistent identification."""
        raise NotImplementedError

    @abstractmethod
    async def fetch_product(self, url: str) -> Dict[str, Any]:
        """Fetch product data from the source. Returns raw product dict."""
        raise NotImplementedError

    @abstractmethod
    async def extract_product_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw data into a standard product data dict."""
        raise NotImplementedError
