import hashlib
import hmac
import json
import re
from typing import Any, Dict, Mapping
from urllib.parse import quote, urlencode

import httpx

from app.core.config import settings
from app.core.encryption import decrypt_value
from app.core.exceptions import BadGatewayException, BadRequestException
from app.core.logging import get_logger
from app.models.store import StoreStatus
from app.services.shopify.base import ShopifyProvider

logger = get_logger(__name__)
SHOP_DOMAIN_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$")


class RealShopifyProvider(ShopifyProvider):
    def _get_api_version(self) -> str:
        return settings.SHOPIFY_API_VERSION or "2026-07"

    @staticmethod
    def _normalize_shop_domain(shop_domain: str) -> str:
        value = (shop_domain or "").strip().lower().rstrip(".")
        if not SHOP_DOMAIN_RE.fullmatch(value):
            raise BadRequestException("Invalid Shopify shop domain")
        return value

    @staticmethod
    def _require_oauth_config() -> None:
        if not settings.SHOPIFY_API_KEY or not settings.SHOPIFY_API_SECRET or not settings.SHOPIFY_REDIRECT_URI:
            raise BadRequestException("Shopify integration is not configured")

    def _graphql_url(self, shop_domain: str) -> str:
        shop = self._normalize_shop_domain(shop_domain)
        return f"https://{shop}/admin/api/{self._get_api_version()}/graphql.json"

    @staticmethod
    def _get_headers(access_token: str) -> Dict[str, str]:
        if not access_token:
            raise BadRequestException("Shopify store credentials are missing; reconnect your store")
        return {"X-Shopify-Access-Token": access_token, "Content-Type": "application/json"}

    @staticmethod
    def _decode_json(response: httpx.Response) -> Dict[str, Any]:
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise BadGatewayException("Shopify returned an invalid response") from exc
        if not isinstance(data, dict):
            raise BadGatewayException("Shopify returned an invalid response")
        return data

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        reauthorize_on_401: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=settings.SHOPIFY_REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return self._decode_json(response)
        except httpx.TimeoutException as exc:
            raise BadGatewayException("Shopify request timed out; try again") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401 and reauthorize_on_401:
                raise BadRequestException("Shopify authorization expired; reconnect your store") from exc
            if exc.response.status_code in {401, 403}:
                raise BadGatewayException("Shopify authorization failed; reconnect your store") from exc
            raise BadGatewayException("Shopify request failed; try again") from exc
        except httpx.RequestError as exc:
            raise BadGatewayException("Shopify is temporarily unavailable; try again") from exc

    async def _graphql(
        self,
        access_token: str,
        shop_domain: str,
        query: str,
        variables: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        response = await self._request_json(
            "POST",
            self._graphql_url(shop_domain),
            headers=self._get_headers(access_token),
            json={"query": query, "variables": variables or {}},
        )
        if response.get("errors"):
            raise BadGatewayException("Shopify GraphQL request failed; try again")
        data = response.get("data")
        if not isinstance(data, dict):
            raise BadGatewayException("Shopify returned an invalid response")
        return data

    @staticmethod
    def _require_mutation_result(data: Dict[str, Any], field: str, resource: str) -> Dict[str, Any]:
        payload = data.get(field)
        if not isinstance(payload, dict):
            raise BadGatewayException("Shopify returned an invalid response")
        if payload.get("userErrors"):
            raise BadRequestException(f"Shopify rejected the {resource} data")
        return payload

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

    def get_install_url(self, shop_domain: str, state: str) -> str:
        self._require_oauth_config()
        shop = self._normalize_shop_domain(shop_domain)
        params = {
            "client_id": settings.SHOPIFY_API_KEY,
            "scope": settings.SHOPIFY_SCOPES,
            "redirect_uri": settings.SHOPIFY_REDIRECT_URI,
            "state": state,
        }
        return f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"

    def verify_callback_hmac(self, query_params: Mapping[str, str]) -> None:
        self._require_oauth_config()
        supplied = query_params.get("hmac", "")
        if not supplied:
            raise BadRequestException("Invalid Shopify OAuth callback")
        message = "&".join(
            f"{key}={value}" for key, value in sorted(query_params.items()) if key != "hmac"
        )
        expected = hmac.new(
            settings.SHOPIFY_API_SECRET.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, supplied):
            raise BadRequestException("Invalid Shopify OAuth callback")

    async def exchange_code(self, code: str, shop_domain: str) -> Dict[str, Any]:
        self._require_oauth_config()
        if not code:
            raise BadRequestException("Missing Shopify authorization code")
        shop = self._normalize_shop_domain(shop_domain)
        return await self._request_json(
            "POST",
            f"https://{shop}/admin/oauth/access_token",
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_id": settings.SHOPIFY_API_KEY,
                "client_secret": settings.SHOPIFY_API_SECRET,
                "code": code,
                "expiring": "1",
            },
        )

    async def refresh_access_token(self, refresh_token: str, shop_domain: str) -> Dict[str, Any]:
        self._require_oauth_config()
        if not refresh_token:
            raise BadRequestException("Shopify refresh token is missing; reconnect your store")
        shop = self._normalize_shop_domain(shop_domain)
        return await self._request_json(
            "POST",
            f"https://{shop}/admin/oauth/access_token",
            reauthorize_on_401=True,
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_id": settings.SHOPIFY_API_KEY,
                "client_secret": settings.SHOPIFY_API_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )

    async def get_shop(self, access_token: str, shop_domain: str = "") -> Dict[str, Any]:
        data = await self._graphql(
            access_token,
            shop_domain,
            """
            query VelnioShopIdentity {
              shop {
                name
                email
                currencyCode
                myshopifyDomain
                billingAddress { countryCodeV2 }
              }
            }
            """,
        )
        shop_data = data.get("shop")
        if not isinstance(shop_data, dict):
            raise BadGatewayException("Shopify returned an invalid shop response")
        billing = shop_data.get("billingAddress") or {}
        return {
            "name": shop_data.get("name", ""),
            "domain": shop_data.get("myshopifyDomain") or shop_domain,
            "email": shop_data.get("email", ""),
            "currency": shop_data.get("currencyCode", "USD"),
            "country_code": billing.get("countryCodeV2", "US") if isinstance(billing, dict) else "US",
        }

    async def _publish_product_to_online_store(
        self,
        access_token: str,
        shop_domain: str,
        product_id: str,
    ) -> None:
        publications_data = await self._graphql(
            access_token,
            shop_domain,
            """
            query VelnioPublications {
              publications(first: 50) { nodes { id name autoPublish } }
            }
            """,
        )
        connection = publications_data.get("publications")
        nodes = connection.get("nodes", []) if isinstance(connection, dict) else []
        online_store = next(
            (
                node
                for node in nodes
                if isinstance(node, dict) and str(node.get("name", "")).strip().lower() == "online store"
            ),
            None,
        )
        if online_store is None or not online_store.get("id"):
            raise BadRequestException("Shopify Online Store sales channel is required to publish products")

        status_data = await self._graphql(
            access_token,
            shop_domain,
            """
            query VelnioPublicationStatus($id: ID!, $publicationId: ID!) {
              node(id: $id) {
                ... on Product { publishedOnPublication(publicationId: $publicationId) }
              }
            }
            """,
            {"id": product_id, "publicationId": online_store["id"]},
        )
        node = status_data.get("node")
        if isinstance(node, dict) and node.get("publishedOnPublication") is True:
            return

        publish_data = await self._graphql(
            access_token,
            shop_domain,
            """
            mutation VelnioPublishProduct($id: ID!, $input: [PublicationInput!]!) {
              publishablePublish(id: $id, input: $input) {
                userErrors { field message }
              }
            }
            """,
            {"id": product_id, "input": [{"publicationId": online_store["id"]}]},
        )
        self._require_mutation_result(publish_data, "publishablePublish", "publication")

    async def create_product(
        self,
        access_token: str,
        shop_domain: str,
        product_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        tags = product_data.get("tags") or []
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        product_input = {
            "title": product_data.get("title") or "Velnio Product",
            "descriptionHtml": product_data.get("body_html") or "",
            "vendor": product_data.get("vendor") or "Velnio",
            "productType": product_data.get("product_type") or "",
            "status": str(product_data.get("status") or "ACTIVE").upper(),
            "tags": tags,
        }
        media = [
            {"originalSource": image["src"], "mediaContentType": "IMAGE"}
            for image in product_data.get("images", [])
            if isinstance(image, dict) and image.get("src")
        ]
        data = await self._graphql(
            access_token,
            shop_domain,
            """
            mutation VelnioCreateProduct($product: ProductCreateInput!, $media: [CreateMediaInput!]) {
              productCreate(product: $product, media: $media) {
                product { id title status variants(first: 1) { nodes { id } } }
                userErrors { field message }
              }
            }
            """,
            {"product": product_input, "media": media},
        )
        payload = self._require_mutation_result(data, "productCreate", "product")
        product = payload.get("product")
        if not isinstance(product, dict) or not product.get("id"):
            raise BadGatewayException("Shopify did not return a valid product")

        requested_variants = product_data.get("variants") or []
        nodes = ((product.get("variants") or {}).get("nodes") or []) if isinstance(product.get("variants"), dict) else []
        if requested_variants and nodes and isinstance(nodes[0], dict) and nodes[0].get("id"):
            requested = requested_variants[0]
            variant_input: Dict[str, Any] = {"id": nodes[0]["id"]}
            if requested.get("price") is not None:
                variant_input["price"] = str(requested["price"])
            if requested.get("compare_at_price") is not None:
                variant_input["compareAtPrice"] = str(requested["compare_at_price"])
            if requested.get("sku"):
                variant_input["inventoryItem"] = {"sku": str(requested["sku"]), "tracked": True}
            variant_data = await self._graphql(
                access_token,
                shop_domain,
                """
                mutation VelnioUpdateVariant($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                    productVariants { id price compareAtPrice }
                    userErrors { field message }
                  }
                }
                """,
                {"productId": product["id"], "variants": [variant_input]},
            )
            self._require_mutation_result(variant_data, "productVariantsBulkUpdate", "variant")

        await self._publish_product_to_online_store(access_token, shop_domain, str(product["id"]))
        return product

    async def create_page(
        self,
        access_token: str,
        shop_domain: str,
        page_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        data = await self._graphql(
            access_token,
            shop_domain,
            """
            mutation VelnioCreatePage($page: PageCreateInput!) {
              pageCreate(page: $page) {
                page { id title handle }
                userErrors { field message code }
              }
            }
            """,
            {
                "page": {
                    "title": page_data.get("title") or "Velnio Landing Page",
                    "body": page_data.get("body_html") or "",
                    "isPublished": bool(page_data.get("published", True)),
                }
            },
        )
        payload = self._require_mutation_result(data, "pageCreate", "page")
        page = payload.get("page")
        if not isinstance(page, dict) or not page.get("id"):
            raise BadGatewayException("Shopify did not return a valid page")
        return page

    async def publish_product(self, product, store=None) -> Dict[str, Any]:
        access_token, shop_domain = self._store_credentials(store)
        product_data: Dict[str, Any] = {
            "title": product.name,
            "body_html": product.description or "",
            "vendor": "Velnio",
            "product_type": "General",
            "status": "ACTIVE",
            "tags": ["velnio", f"velnio-product:{product.id}"],
        }
        if product.images:
            product_data["images"] = [
                {"src": img.image_url, "position": img.position}
                for img in sorted(product.images, key=lambda item: item.position)
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
        parts = []
        if angle:
            parts += [f"<h2>{angle.hook}</h2>", f"<p>{angle.main_promise}</p>", f"<p>{angle.description}</p>"]
        if offer:
            if offer.headline:
                parts.append(f"<h3>{offer.headline}</h3>")
            if offer.bonus_text:
                parts.append(f"<p><strong>{offer.bonus_text}</strong></p>")
            if offer.urgency_text:
                parts.append(f"<p><em>{offer.urgency_text}</em></p>")
        tags = ["velnio", f"velnio-campaign:{campaign.id}"]
        if campaign.target_country:
            tags.append(f"market:{campaign.target_country}")
        product_data: Dict[str, Any] = {
            "title": product_title,
            "body_html": "\n".join(parts) or (product.description or ""),
            "vendor": "Velnio",
            "product_type": "Campaign",
            "status": "ACTIVE",
            "tags": tags,
            "variants": [],
        }
        if campaign.selling_price:
            product_data["variants"].append(
                {
                    "price": str(campaign.selling_price),
                    "compare_at_price": str(offer.compare_at_price) if offer and offer.compare_at_price else None,
                    "sku": f"CAMPAIGN-{str(campaign.id)[:8]}",
                }
            )
        if product.images:
            product_data["images"] = [
                {"src": img.image_url, "position": img.position}
                for img in sorted(product.images, key=lambda item: item.position)
            ]
        shopify_product = await self.create_product(access_token, shop_domain, product_data)

        shopify_page_id = shopify_page_handle = shopify_page_url = None
        if landing:
            page = await self.create_page(
                access_token,
                shop_domain,
                {
                    "title": landing.title or product_title,
                    "body_html": renderer.render(landing),
                    "published": True,
                },
            )
            shopify_page_id = str(page["id"])
            shopify_page_handle = page.get("handle")
            shopify_page_url = (
                f"https://{shop_domain}/pages/{quote(str(shopify_page_handle), safe='')}"
                if shopify_page_handle
                else None
            )
        return {
            "status": "published",
            "provider": "shopify",
            "shopify_product_id": str(shopify_product["id"]),
            "shopify_page_id": shopify_page_id,
            "shopify_page_handle": shopify_page_handle,
            "shopify_page_url": shopify_page_url,
        }

    async def disconnect(self) -> None:
        return None
