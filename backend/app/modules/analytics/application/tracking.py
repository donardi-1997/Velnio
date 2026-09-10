from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.campaign import Campaign
from app.models.tracking import LandingVariant, TrackingEvent, VALID_EVENT_TYPES


@dataclass(slots=True)
class TrackingInput:
    event_type: str
    session_id: str
    visitor_id: str | None = None
    landing_variant_id: UUID | str | None = None
    source: str | None = None
    medium: str | None = None
    campaign_source: str | None = None
    country: str | None = None
    device_type: str | None = None
    referrer: str | None = None
    extra_data: dict[str, Any] | None = None
    revenue: float | None = None
    currency: str | None = None
    external_event_id: str | None = None
    occurred_at: str | None = None


class TrackingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def validate(data) -> None:
        if data.event_type not in VALID_EVENT_TYPES:
            raise BadRequestException(
                f"Invalid event type: {data.event_type}. Must be one of: {', '.join(sorted(VALID_EVENT_TYPES))}"
            )
        if not data.session_id or len(data.session_id) > 255:
            raise BadRequestException("session_id is required and must be <= 255 characters")
        if data.revenue is not None and data.revenue < 0:
            raise BadRequestException("revenue must be >= 0")
        if data.extra_data and len(str(data.extra_data)) > 10000:
            raise BadRequestException("extra_data must be <= 10KB")

    @staticmethod
    def parse_occurred_at(data) -> datetime:
        if data.occurred_at:
            try:
                return datetime.fromisoformat(data.occurred_at.replace("Z", "+00:00"))
            except ValueError:
                pass
        return datetime.now(timezone.utc)

    async def _campaign(self, tracking_key: str) -> Campaign:
        result = await self.db.execute(select(Campaign).where(Campaign.tracking_key == tracking_key))
        campaign = result.scalar_one_or_none()
        if campaign is None:
            raise NotFoundException("Campaign not found")
        return campaign

    async def _resolve_variant_id(self, campaign: Campaign, data) -> UUID | None:
        raw_variant_id = getattr(data, "landing_variant_id", None)
        extra_data = getattr(data, "extra_data", None)
        if raw_variant_id is None and extra_data and "variant_id" in extra_data:
            raw_variant_id = extra_data["variant_id"]
        if raw_variant_id in {None, ""}:
            return None
        try:
            variant_id = raw_variant_id if isinstance(raw_variant_id, UUID) else UUID(str(raw_variant_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise BadRequestException("Invalid landing_variant_id") from exc

        result = await self.db.execute(
            select(LandingVariant.id).where(
                LandingVariant.id == variant_id,
                LandingVariant.campaign_id == campaign.id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise BadRequestException("Landing variant does not belong to this campaign")
        return variant_id

    @staticmethod
    def _event(
        campaign: Campaign,
        data,
        occurred_at: datetime,
        variant_id: UUID | None,
    ) -> TrackingEvent:
        return TrackingEvent(
            workspace_id=campaign.workspace_id,
            campaign_id=campaign.id,
            landing_variant_id=variant_id,
            event_type=data.event_type,
            session_id=data.session_id,
            visitor_id=data.visitor_id,
            source=data.source,
            medium=data.medium,
            campaign_source=data.campaign_source,
            country=data.country,
            device_type=data.device_type,
            referrer=data.referrer,
            extra_data=data.extra_data,
            revenue=data.revenue,
            currency=data.currency,
            external_event_id=data.external_event_id,
            occurred_at=occurred_at,
        )

    async def _assert_external_ids_available(self, campaign_id: UUID, external_ids: list[str]) -> None:
        if not external_ids:
            return
        if len(external_ids) != len(set(external_ids)):
            raise BadRequestException("Duplicate event: external_event_id repeated in request")
        result = await self.db.execute(
            select(TrackingEvent.external_event_id).where(
                TrackingEvent.campaign_id == campaign_id,
                TrackingEvent.external_event_id.in_(external_ids),
            )
        )
        if result.first() is not None:
            raise BadRequestException("Duplicate event: external_event_id already recorded")

    async def track(self, tracking_key: str, data) -> TrackingEvent:
        self.validate(data)
        campaign = await self._campaign(tracking_key)
        if data.external_event_id:
            await self._assert_external_ids_available(campaign.id, [data.external_event_id])
        variant_id = await self._resolve_variant_id(campaign, data)
        event = self._event(campaign, data, self.parse_occurred_at(data), variant_id)
        self.db.add(event)
        await self.db.flush()
        return event

    async def track_batch(self, tracking_key: str, event_data: list) -> int:
        campaign = await self._campaign(tracking_key)
        for data in event_data:
            self.validate(data)
        await self._assert_external_ids_available(
            campaign.id,
            [data.external_event_id for data in event_data if data.external_event_id],
        )

        events = []
        for data in event_data:
            variant_id = await self._resolve_variant_id(campaign, data)
            events.append(self._event(campaign, data, self.parse_occurred_at(data), variant_id))
        self.db.add_all(events)
        await self.db.flush()
        return len(events)
