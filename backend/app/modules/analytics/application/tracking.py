from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.campaign import Campaign
from app.models.tracking import TrackingEvent, VALID_EVENT_TYPES


class TrackingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def validate(data) -> None:
        if data.event_type not in VALID_EVENT_TYPES:
            raise BadRequestException(
                f"Invalid event type: {data.event_type}. Must be one of: {', '.join(VALID_EVENT_TYPES)}"
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

    @staticmethod
    def _event(campaign: Campaign, data, occurred_at: datetime) -> TrackingEvent:
        variant_id = None
        if data.extra_data and "variant_id" in data.extra_data:
            try:
                variant_id = UUID(data.extra_data["variant_id"])
            except (ValueError, TypeError):
                pass
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

    async def track(self, tracking_key: str, data) -> TrackingEvent:
        self.validate(data)
        campaign = await self._campaign(tracking_key)
        if data.event_type == "PURCHASE" and data.external_event_id:
            existing = await self.db.execute(
                select(TrackingEvent).where(
                    TrackingEvent.campaign_id == campaign.id,
                    TrackingEvent.external_event_id == data.external_event_id,
                )
            )
            if existing.scalar_one_or_none():
                raise BadRequestException("Duplicate event: external_event_id already recorded")
        event = self._event(campaign, data, self.parse_occurred_at(data))
        self.db.add(event)
        await self.db.flush()
        return event

    async def track_batch(self, tracking_key: str, event_data: list) -> int:
        campaign = await self._campaign(tracking_key)
        events = []
        for data in event_data:
            self.validate(data)
            events.append(self._event(campaign, data, self.parse_occurred_at(data)))
        self.db.add_all(events)
        await self.db.flush()
        return len(events)
