from __future__ import annotations

import base64
import hashlib
import hmac
import json
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, UnauthorizedException
from app.models.campaign import Campaign
from app.models.store import Store
from app.models.tracking import LandingVariant, TrackingEvent
from app.modules.analytics.application.tracking import TrackingInput, TrackingService
from app.services.shopify.real_provider import RealShopifyProvider


class ShopifyOrderWebhookService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.tracking = TrackingService(db)

    @staticmethod
    def verify_hmac(raw_body: bytes, supplied_hmac: str) -> None:
        if not settings.SHOPIFY_API_SECRET or not supplied_hmac:
            raise UnauthorizedException("Invalid Shopify webhook signature")
        digest = hmac.new(
            settings.SHOPIFY_API_SECRET.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).digest()
        expected = base64.b64encode(digest).decode("ascii")
        if not hmac.compare_digest(expected, supplied_hmac):
            raise UnauthorizedException("Invalid Shopify webhook signature")

    @staticmethod
    def _properties(line_item: dict[str, Any]) -> dict[str, str]:
        values: dict[str, str] = {}
        properties = line_item.get("properties") or []
        if not isinstance(properties, list):
            return values
        for item in properties:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            value = item.get("value")
            if isinstance(name, str) and value is not None:
                values[name] = str(value)
        return values

    @staticmethod
    def _shopify_numeric_id(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        tail = text.rsplit("/", 1)[-1]
        return tail if tail.isdigit() else text

    @staticmethod
    def _line_revenue(line_item: dict[str, Any]) -> float:
        try:
            price = Decimal(str(line_item.get("price") or "0"))
            quantity = Decimal(str(line_item.get("quantity") or "0"))
            gross = price * quantity
            discounts = Decimal("0")
            for allocation in line_item.get("discount_allocations") or []:
                if isinstance(allocation, dict):
                    discounts += Decimal(str(allocation.get("amount") or "0"))
            return float(max(Decimal("0"), gross - discounts))
        except (InvalidOperation, TypeError, ValueError):
            return 0.0

    async def _campaign_for_line(
        self,
        tracking_key: str,
        shop_domain: str,
        product_id: Any,
    ) -> Campaign | None:
        result = await self.db.execute(
            select(Campaign).where(Campaign.tracking_key == tracking_key)
        )
        campaign = result.scalar_one_or_none()
        if campaign is None or campaign.store_id is None:
            return None

        store = (
            await self.db.execute(
                select(Store).where(
                    Store.id == campaign.store_id,
                    Store.workspace_id == campaign.workspace_id,
                    Store.shop_domain == shop_domain,
                )
            )
        ).scalar_one_or_none()
        if store is None:
            return None

        expected_product_id = self._shopify_numeric_id(campaign.external_product_id)
        actual_product_id = self._shopify_numeric_id(product_id)
        if (
            expected_product_id is None
            or actual_product_id is None
            or actual_product_id != expected_product_id
        ):
            return None
        return campaign

    async def _safe_variant_id(self, campaign_id: UUID, raw_value: str | None) -> UUID | None:
        if not raw_value:
            return None
        try:
            variant_id = UUID(raw_value)
        except (TypeError, ValueError):
            return None
        result = await self.db.execute(
            select(LandingVariant.id).where(
                LandingVariant.id == variant_id,
                LandingVariant.campaign_id == campaign_id,
            )
        )
        return variant_id if result.scalar_one_or_none() is not None else None

    async def ingest(
        self,
        raw_body: bytes,
        supplied_hmac: str,
        shop_domain: str,
        topic: str,
    ) -> int:
        self.verify_hmac(raw_body, supplied_hmac)
        if topic != "orders/create":
            raise BadRequestException("Unsupported Shopify webhook topic")
        shop = RealShopifyProvider._normalize_shop_domain(shop_domain)

        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise BadRequestException("Invalid Shopify webhook payload") from exc
        if not isinstance(payload, dict) or payload.get("id") is None:
            raise BadRequestException("Invalid Shopify webhook payload")

        order_id = str(payload["id"])
        currency = str(payload.get("currency") or "USD")[:3].upper()
        accepted = 0
        line_items = payload.get("line_items") or []
        if not isinstance(line_items, list):
            raise BadRequestException("Invalid Shopify webhook payload")

        for index, line_item in enumerate(line_items):
            if not isinstance(line_item, dict):
                continue
            properties = self._properties(line_item)
            tracking_key = properties.get("_velnio_tracking_key")
            if not tracking_key:
                continue

            campaign = await self._campaign_for_line(
                tracking_key,
                shop,
                line_item.get("product_id"),
            )
            if campaign is None:
                continue

            line_id = str(line_item.get("id") or index)
            external_event_id = f"shopify-order:{order_id}:line:{line_id}"[:255]
            existing = await self.db.execute(
                select(TrackingEvent.id).where(
                    TrackingEvent.campaign_id == campaign.id,
                    TrackingEvent.external_event_id == external_event_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue

            variant_id = await self._safe_variant_id(
                campaign.id,
                properties.get("_velnio_variant_id"),
            )
            session_id = (
                properties.get("_velnio_session_id")
                or f"shopify-order-{order_id}"
            )[:255]
            visitor_id = properties.get("_velnio_visitor_id")
            if visitor_id:
                visitor_id = visitor_id[:255]

            await self.tracking.track(
                tracking_key,
                TrackingInput(
                    event_type="PURCHASE",
                    session_id=session_id,
                    visitor_id=visitor_id,
                    landing_variant_id=variant_id,
                    source="shopify",
                    medium="order_webhook",
                    revenue=self._line_revenue(line_item),
                    currency=currency,
                    external_event_id=external_event_id,
                    extra_data={
                        "shopify_order_id": order_id,
                        "shopify_line_item_id": line_id,
                    },
                ),
            )
            accepted += 1

        return accepted
