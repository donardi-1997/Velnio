from __future__ import annotations

from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.core.encryption import decrypt_value
from app.core.exceptions import BadGatewayException, BadRequestException
from app.models.store import Store


def get_public_api_origin() -> str:
    parsed = urlparse(settings.SHOPIFY_REDIRECT_URI)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise BadRequestException("Shopify redirect URI is not configured correctly")
    if settings.APP_ENV == "production" and parsed.scheme != "https":
        raise BadRequestException("Shopify production callbacks require HTTPS")
    return f"{parsed.scheme}://{parsed.netloc}"


class ShopifyWebhookRegistrar:
    """Idempotently keeps the shop-scoped ORDERS_CREATE webhook installed."""

    async def ensure_orders_create(self, store: Store) -> None:
        if not store.access_token_encrypted or not store.shop_domain:
            raise BadRequestException("Shopify store credentials are missing; reconnect your store")
        try:
            access_token = decrypt_value(store.access_token_encrypted)
        except Exception as exc:
            raise BadRequestException("Shopify store credentials are invalid; reconnect your store") from exc
        if not access_token:
            raise BadRequestException("Shopify store credentials are invalid; reconnect your store")

        webhook_uri = f"{get_public_api_origin()}/api/stores/shopify/webhooks/orders-create"
        endpoint = (
            f"https://{store.shop_domain}/admin/api/"
            f"{settings.SHOPIFY_API_VERSION or '2026-07'}/graphql.json"
        )
        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        }

        query = """
        query VelnioOrderWebhooks {
          webhookSubscriptions(first: 20, topics: ORDERS_CREATE) {
            edges { node { id topic uri } }
          }
        }
        """
        data = await self._graphql(endpoint, headers, query)
        connection = data.get("webhookSubscriptions") or {}
        edges = connection.get("edges", []) if isinstance(connection, dict) else []
        for edge in edges:
            node = edge.get("node", {}) if isinstance(edge, dict) else {}
            if node.get("topic") == "ORDERS_CREATE" and node.get("uri") == webhook_uri:
                return

        mutation = """
        mutation VelnioCreateOrderWebhook($webhookSubscription: WebhookSubscriptionInput!) {
          webhookSubscriptionCreate(
            topic: ORDERS_CREATE,
            webhookSubscription: $webhookSubscription
          ) {
            webhookSubscription { id topic uri }
            userErrors { field message }
          }
        }
        """
        created = await self._graphql(
            endpoint,
            headers,
            mutation,
            {"webhookSubscription": {"uri": webhook_uri}},
        )
        payload = created.get("webhookSubscriptionCreate")
        if not isinstance(payload, dict) or payload.get("userErrors"):
            raise BadRequestException(
                "Shopify could not enable order conversion tracking; reconnect the store with the required permissions"
            )
        webhook = payload.get("webhookSubscription")
        if not isinstance(webhook, dict) or webhook.get("uri") != webhook_uri:
            raise BadGatewayException("Shopify returned an invalid webhook subscription response")

    @staticmethod
    async def _graphql(
        endpoint: str,
        headers: dict[str, str],
        query: str,
        variables: dict | None = None,
    ) -> dict:
        try:
            async with httpx.AsyncClient(timeout=settings.SHOPIFY_REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    endpoint,
                    headers=headers,
                    json={"query": query, "variables": variables or {}},
                )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise BadGatewayException("Shopify webhook setup timed out; try again") from exc
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            raise BadGatewayException("Shopify webhook setup failed; try again") from exc
        if not isinstance(payload, dict) or payload.get("errors"):
            raise BadGatewayException("Shopify webhook setup failed; try again")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise BadGatewayException("Shopify returned an invalid webhook setup response")
        return data
