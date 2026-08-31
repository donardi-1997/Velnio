import hashlib
from typing import Any, Dict
from app.services.import_engine.base import ProductSourceProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


class MockProductProvider(ProductSourceProvider):
    def can_handle(self, url: str) -> bool:
        return True

    def normalize_url(self, url: str) -> str:
        return url.rstrip("/")

    async def fetch_product(self, url: str) -> Dict[str, Any]:
        logger.info(f"[mock] Fetching product from {url}")
        h = hashlib.md5(url.encode()).hexdigest()[:8]
        return {
            "url": url,
            "mock": True,
            "html": f"<html><head><title>Mock Product {h}</title></head><body></body></html>",
            "content_type": "text/html",
            "status_code": 200,
        }

    async def extract_product_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        url = raw_data.get("url", "unknown")
        h = hashlib.md5(url.encode()).hexdigest()[:8]
        return {
            "source_url": url,
            "name": f"Mock Product {h}",
            "description": f"This is a mock product imported from {url}. Features include durability, modern design, and excellent value.",
            "price": 29.99,
            "currency": "USD",
            "images": [f"/storage/mock/product_{h}.png"],
            "source_domain": "mock.example.com",
        }
