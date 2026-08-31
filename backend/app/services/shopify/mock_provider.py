import uuid
from typing import Any, Dict, Optional
from app.services.shopify.base import ShopifyProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


class MockShopifyProvider(ShopifyProvider):
    def get_install_url(self) -> str:
        return "https://mock-shop.myshopify.com/admin/oauth/authorize?mock=true"

    async def handle_callback(self, code: str, shop: str) -> Dict[str, Any]:
        return {
            "access_token": f"mock_token_{uuid.uuid4().hex[:8]}",
            "shop": shop,
            "scope": "read_products,write_products",
        }

    async def get_shop(self, access_token: str) -> Dict[str, Any]:
        return {
            "name": "Mock Shop",
            "domain": "mock-shop.myshopify.com",
            "email": "admin@mock-shop.com",
            "currency": "USD",
        }

    async def create_product(self, access_token: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": f"mock_product_{uuid.uuid4().hex[:8]}",
            "title": product_data.get("title", "Product"),
            "status": "active",
        }

    async def create_page(self, access_token: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": f"mock_page_{uuid.uuid4().hex[:8]}",
            "title": page_data.get("title", "Page"),
            "published": True,
        }

    async def publish_product(self, product, store=None) -> Dict[str, Any]:
        product_id = f"mock_product_{uuid.uuid4().hex[:8]}"
        page_id = f"mock_page_{uuid.uuid4().hex[:8]}"
        logger.info(f"Mock publishing product {product.name} - ID: {product_id}")
        return {
            "status": "published",
            "provider": "mock",
            "shopify_product_id": product_id,
            "shopify_page_id": page_id,
        }

    async def publish_campaign(self, campaign, product, store, angle, landing, offer) -> Dict[str, Any]:
        product_id = f"mock_product_{uuid.uuid4().hex[:8]}"
        page_id = f"mock_page_{uuid.uuid4().hex[:8]}"
        logger.info(f"Mock publishing campaign '{campaign.name}' - Product: {product_id}, Page: {page_id}")

        offer_info = ""
        if offer:
            offer_info = f" | Offer: {offer.offer_type} @ ${offer.primary_price}"

        landing_info = ""
        if landing:
            landing_info = f" | Landing: {landing.title}"

        logger.info(f"Campaign details: country={campaign.target_country}, currency={campaign.currency}, price={campaign.selling_price}{offer_info}{landing_info}")

        return {
            "status": "published",
            "provider": "mock",
            "shopify_product_id": product_id,
            "shopify_page_id": page_id,
        }

    async def disconnect(self) -> None:
        pass
