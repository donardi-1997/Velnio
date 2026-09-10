import uuid
from typing import Any, Dict, Mapping

from app.core.logging import get_logger
from app.services.shopify.base import ShopifyProvider

logger = get_logger(__name__)


class MockShopifyProvider(ShopifyProvider):
    def get_install_url(self, shop_domain: str, state: str) -> str:
        return f"https://{shop_domain}/admin/oauth/authorize?mock=true&state={state}"

    def verify_callback_hmac(self, query_params: Mapping[str, str]) -> None:
        return None

    async def exchange_code(self, code: str, shop_domain: str) -> Dict[str, Any]:
        return {
            "access_token": f"mock_token_{uuid.uuid4().hex[:8]}",
            "refresh_token": f"mock_refresh_{uuid.uuid4().hex[:8]}",
            "expires_in": 3600,
            "refresh_token_expires_in": 7776000,
            "shop": shop_domain,
            "scope": "read_products,write_products",
        }

    async def refresh_access_token(self, refresh_token: str, shop_domain: str) -> Dict[str, Any]:
        return await self.exchange_code("refresh", shop_domain)

    async def get_shop(self, access_token: str, shop_domain: str = "") -> Dict[str, Any]:
        return {
            "name": "Mock Shop",
            "domain": shop_domain or "mock-shop.myshopify.com",
            "email": "admin@mock-shop.com",
            "currency": "USD",
            "country_code": "US",
        }

    async def create_product(
        self,
        access_token: str,
        shop_domain: str,
        product_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "id": f"mock_product_{uuid.uuid4().hex[:8]}",
            "title": product_data.get("title", "Product"),
            "status": "active",
        }

    async def create_page(
        self,
        access_token: str,
        shop_domain: str,
        page_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "id": f"mock_page_{uuid.uuid4().hex[:8]}",
            "title": page_data.get("title", "Page"),
            "published": True,
        }

    async def publish_product(self, product, store=None) -> Dict[str, Any]:
        product_id = f"mock_product_{uuid.uuid4().hex[:8]}"
        page_id = f"mock_page_{uuid.uuid4().hex[:8]}"
        logger.info("Mock publishing product %s - ID: %s", product.name, product_id)
        return {
            "status": "published",
            "provider": "mock",
            "shopify_product_id": product_id,
            "shopify_page_id": page_id,
        }

    async def publish_campaign(self, campaign, product, store, angle, landing, offer) -> Dict[str, Any]:
        product_id = f"mock_product_{uuid.uuid4().hex[:8]}"
        page_id = f"mock_page_{uuid.uuid4().hex[:8]}"
        logger.info("Mock publishing campaign '%s' - Product: %s, Page: %s", campaign.name, product_id, page_id)
        return {
            "status": "published",
            "provider": "mock",
            "shopify_product_id": product_id,
            "shopify_page_id": page_id,
        }

    async def disconnect(self) -> None:
        return None
