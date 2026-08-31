from typing import Any, Dict, Optional
from app.services.shopify.base import ShopifyProvider
from app.core.config import settings
from app.core.logging import get_logger
import httpx

logger = get_logger(__name__)


class RealShopifyProvider(ShopifyProvider):
    def _get_api_version(self) -> str:
        return settings.SHOPIFY_API_VERSION or "2024-10"

    def _get_base_url(self, shop_domain: str) -> str:
        return f"https://{shop_domain}/admin/api/{self._get_api_version()}"

    def _get_headers(self, access_token: str) -> Dict[str, str]:
        return {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        }

    def get_install_url(self) -> str:
        scopes = settings.SHOPIFY_SCOPES
        redirect_uri = settings.SHOPIFY_REDIRECT_URI
        return (
            f"https://shopify.com/admin/oauth/authorize"
            f"?client_id={settings.SHOPIFY_API_KEY}"
            f"&scope={scopes}"
            f"&redirect_uri={redirect_uri}"
        )

    async def handle_callback(self, code: str, shop: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{shop}/admin/oauth/access_token",
                json={
                    "client_id": settings.SHOPIFY_API_KEY,
                    "client_secret": settings.SHOPIFY_API_SECRET,
                    "code": code,
                },
            )
            response.raise_for_status()
            data = response.json()
            return {
                "access_token": data["access_token"],
                "shop": shop,
                "scope": data.get("scope", ""),
            }

    async def get_shop(self, access_token: str, shop_domain: str = "") -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._get_base_url(shop_domain)}/shop.json",
                headers=self._get_headers(access_token),
            )
            response.raise_for_status()
            shop_data = response.json().get("shop", {})
            return {
                "name": shop_data.get("name", ""),
                "domain": shop_data.get("domain", ""),
                "email": shop_data.get("email", ""),
                "currency": shop_data.get("currency", "USD"),
            }

    async def create_product(self, access_token: str, shop_domain: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._get_base_url(shop_domain)}/products.json",
                headers=self._get_headers(access_token),
                json={"product": product_data},
            )
            response.raise_for_status()
            return response.json().get("product", {})

    async def create_page(self, access_token: str, shop_domain: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._get_base_url(shop_domain)}/pages.json",
                headers=self._get_headers(access_token),
                json={"page": page_data},
            )
            response.raise_for_status()
            return response.json().get("page", {})

    async def publish_product(self, product, store=None) -> Dict[str, Any]:
        access_token = store.access_token_encrypted if store else settings.SHOPIFY_API_KEY
        shop_domain = store.shop_domain if store else ""

        if not access_token or not shop_domain:
            raise ValueError("Shopify store not connected. Please connect your store first.")

        product_data = {
            "title": product.name,
            "body_html": product.description or "",
            "vendor": "Velnio",
            "product_type": "General",
            "status": "active",
        }

        if product.images:
            product_data["images"] = [
                {"src": img.image_url, "position": img.position}
                for img in sorted(product.images, key=lambda x: x.position)
            ]

        shopify_product = await self.create_product(access_token, shop_domain, product_data)

        return {
            "status": "published",
            "provider": "shopify",
            "shopify_product_id": str(shopify_product.get("id", "")),
            "shopify_page_id": None,
        }

    async def publish_campaign(self, campaign, product, store, angle, landing, offer) -> Dict[str, Any]:
        access_token = store.access_token_encrypted if store else settings.SHOPIFY_API_KEY
        shop_domain = store.shop_domain if store else ""

        if not access_token or not shop_domain:
            raise ValueError("Shopify store not connected. Please connect your store first.")

        from app.services.shopify.renderer import ShopifyLandingRenderer
        renderer = ShopifyLandingRenderer()

        product_title = campaign.name or product.name
        product_description_parts = []
        if angle:
            product_description_parts.append(f"<h2>{angle.hook}</h2>")
            product_description_parts.append(f"<p>{angle.main_promise}</p>")
            product_description_parts.append(f"<p>{angle.description}</p>")
        if offer:
            if offer.headline:
                product_description_parts.append(f"<h3>{offer.headline}</h3>")
            if offer.bonus_text:
                product_description_parts.append(f"<p><strong>{offer.bonus_text}</strong></p>")
            if offer.urgency_text:
                product_description_parts.append(f"<p><em>{offer.urgency_text}</em></p>")
        product_description = "\n".join(product_description_parts) or (product.description or "")

        tags = ["velnio"]
        if campaign.target_country:
            tags.append(f"market:{campaign.target_country}")
        if campaign.id:
            tags.append(f"campaign:{str(campaign.id)[:8]}")

        product_data = {
            "title": product_title,
            "body_html": product_description,
            "vendor": "Velnio",
            "product_type": "Campaign",
            "status": "active",
            "tags": ",".join(tags),
            "variants": [],
        }

        if campaign.selling_price:
            product_data["variants"].append({
                "price": str(campaign.selling_price),
                "compare_at_price": str(offer.compare_at_price) if offer and offer.compare_at_price else None,
                "sku": f"CAMPAIGN-{str(campaign.id)[:8]}",
                "inventory_management": "shopify",
            })

        if product.images:
            product_data["images"] = [
                {"src": img.image_url, "position": img.position}
                for img in sorted(product.images, key=lambda x: x.position)
            ]

        shopify_product = await self.create_product(access_token, shop_domain, product_data)
        shopify_product_id = str(shopify_product.get("id", ""))

        shopify_page_id = None
        shopify_page_handle = None
        shopify_page_url = None
        if landing:
            page_content = renderer.render(landing)
            page_data = {
                "title": landing.title or product_title,
                "body_html": page_content,
                "published": True,
            }
            shopify_page = await self.create_page(access_token, shop_domain, page_data)
            shopify_page_id = str(shopify_page.get("id", ""))
            shopify_page_handle = shopify_page.get("handle", None)
            shopify_page_url = f"https://{shop_domain}/pages/{shopify_page_handle}" if shopify_page_handle else None

        return {
            "status": "published",
            "provider": "shopify",
            "shopify_product_id": shopify_product_id,
            "shopify_page_id": shopify_page_id,
            "shopify_page_handle": shopify_page_handle,
            "shopify_page_url": shopify_page_url,
        }

    async def disconnect(self) -> None:
        pass
