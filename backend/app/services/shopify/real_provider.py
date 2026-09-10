import json
import re
from typing import Any, Dict
from urllib.parse import quote, urlencode

import httpx

from app.core.config import settings
from app.core.encryption import decrypt_value
from app.core.exceptions import BadGatewayException, BadRequestException
from app.core.logging import get_logger
from app.models.store import StoreStatus
from app.services.shopify.base import ShopifyProvider

logger = get_logger(__name__)

SHOPIFY_REQUEST_TIMEOUT_SECONDS = 15.0
SHOP_DOMAIN_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$")


class RealShopifyProvider(ShopifyProvider):
    def _get_api_version(self) -> str:
        return settings.SHOPIFY_API_VERSION or "2024-10"

    @staticmethod
    def _normalize_shop_domain(shop_domain: str) -> str:
        value = (shop_domain or "").strip().lower().rstrip(".")
        if not SHOP_DOMAIN_RE.fullmatch(value):
            raise BadRequestException("Invalid Shopify shop domain")
        return value

    def _get_base_url(self, shop_domain: str) -> str:
        normalized = self._normalize_shop_domain(shop_domain)
        return f"https://{normalized}/admin/api/{self._get_api_version()}"

    @staticmethod
    def _get_headers(access_token: str) -> Dict[str, str]:
        if not access_token:
            raise BadRequestException("Shopify store credentials are missing; reconnect your store")
        return {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _decode_json(response: httpx.Response) -> Dict[str, Any]:
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise BadGatewayException("Shopify returned an invalid response") from exc
        if not isinstance(data, dict):
            raise BadGatewayException("Shopify returned an invalid response")
        return data

    async def _request_json(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=SHOPIFY_REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return self._decode_json(response)
        except httpx.TimeoutException as exc:
            raise BadGatewayException("Shopify request timed out; try again") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                raise BadGatewayException("Shopify authorization failed; reconnect your store") from exc
            raise BadGatewayException("Shopify request failed; try again") from exc
        except httpx.RequestError as exc:
            raise BadGatewayException("Shopify is temporarily unavailable; try again") from exc

    def _store_credentials(self, store) -> tuple[str, str]:
        if store is None or store.status != StoreStatus.CONNECTED:
            raise BadRequestException("Shopify store not connected. Please connect your store first.")
        shop_domain = self._normalize_shop_domain(store.shop_domain or "")
        encrypted_token = store.access_token_encrypted
        if not encrypted_token:
            raise BadRequestException("Shopify store credentials are missing; reconnect your store")
        try:
            access_token = decrypt_value(encrypted_token)
        except Exception as exc:
            raise BadRequestException("Shopify store credentials are invalid; reconnect your store") from exc
        if not access_token:
            raise BadRequestException("Shopify store credentials are invalid; reconnect your store")
        return access_token, shop_domain

    def get_install_url(self) -> str:
        params = {
            "client_id": settings.SHOPIFY_API_KEY,
            "scope": settings.SHOPIFY_SCOPES,
            "redirect_uri": settings.SHOPIFY_REDIRECT_URI,
        }
        return f"https://shopify.com/admin/oauth/authorize?{urlencode(params)}"

    async def handle_callback(self, code: str, shop: str) -> Dict[str, Any]:
        if not code:
            raise BadRequestException("Missing Shopify authorization code")
        shop_domain = self._normalize_shop_domain(shop)
        data = await self._request_json(
            "POST",
            f"https://{shop_domain}/admin/oauth/access_token",
            json={
                "client_id": settings.SHOPIFY_API_KEY,
                "client_secret": settings.SHOPIFY_API_SECRET,
                "code": code,
            },
        )
        access_token = data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise BadGatewayException("Shopify did not return a valid access token")
        return {
            "access_token": access_token,
            "shop": shop_domain,
            "scope": data.get("scope", ""),
        }

    async def get_shop(self, access_token: str, shop_domain: str = "") -> Dict[str, Any]:
        data = await self._request_json(
            "GET",
            f"{self._get_base_url(shop_domain)}/shop.json",
            headers=self._get_headers(access_token),
        )
        shop_data = data.get("shop")
        if not isinstance(shop_data, dict):
            raise BadGatewayException("Shopify returned an invalid shop response")
        return {
            "name": shop_data.get("name", ""),
            "domain": shop_data.get("domain", ""),
            "email": shop_data.get("email", ""),
            "currency": shop_data.get("currency", "USD"),
        }

    async def create_product(
        self,
        access_token: str,
        shop_domain: str,
        product_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        data = await self._request_json(
            "POST",
            f"{self._get_base_url(shop_domain)}/products.json",
            headers=self._get_headers(access_token),
            json={"product": product_data},
        )
        product = data.get("product")
        if not isinstance(product, dict) or not product.get("id"):
            raise BadGatewayException("Shopify did not return a valid product")
        return product

    async def create_page(
        self,
        access_token: str,
        shop_domain: str,
        page_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        data = await self._request_json(
            "POST",
            f"{self._get_base_url(shop_domain)}/pages.json",
            headers=self._get_headers(access_token),
            json={"page": page_data},
        )
        page = data.get("page")
        if not isinstance(page, dict) or not page.get("id"):
            raise BadGatewayException("Shopify did not return a valid page")
        return page

    async def publish_product(self, product, store=None) -> Dict[str, Any]:
        access_token, shop_domain = self._store_credentials(store)

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
            "shopify_product_id": str(shopify_product["id"]),
            "shopify_page_id": None,
        }

    async def publish_campaign(self, campaign, product, store, angle, landing, offer) -> Dict[str, Any]:
        access_token, shop_domain = self._store_credentials(store)

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
        shopify_product_id = str(shopify_product["id"])

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
            shopify_page_id = str(shopify_page["id"])
            shopify_page_handle = shopify_page.get("handle")
            shopify_page_url = (
                f"https://{shop_domain}/pages/{quote(str(shopify_page_handle), safe='')}"
                if shopify_page_handle
                else None
            )

        return {
            "status": "published",
            "provider": "shopify",
            "shopify_product_id": shopify_product_id,
            "shopify_page_id": shopify_page_id,
            "shopify_page_handle": shopify_page_handle,
            "shopify_page_url": shopify_page_url,
        }

    async def disconnect(self) -> None:
        return None
