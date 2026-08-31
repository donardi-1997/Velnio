from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.campaign import Campaign
from app.models.tracking import TrackingEvent, VALID_EVENT_TYPES
from app.core.exceptions import BadRequestException, NotFoundException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone

router = APIRouter()


class TrackingEventRequest(BaseModel):
    event_type: str
    session_id: str = Field(..., max_length=255)
    visitor_id: Optional[str] = Field(None, max_length=255)
    source: Optional[str] = Field(None, max_length=50)
    medium: Optional[str] = Field(None, max_length=50)
    campaign_source: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=2)
    device_type: Optional[str] = Field(None, max_length=20)
    referrer: Optional[str] = Field(None, max_length=2048)
    extra_data: Optional[Dict[str, Any]] = None
    revenue: Optional[float] = Field(None)
    currency: Optional[str] = Field(None, max_length=3)
    external_event_id: Optional[str] = Field(None, max_length=255)
    occurred_at: Optional[str] = None


class TrackingBatchRequest(BaseModel):
    events: List[TrackingEventRequest] = Field(..., max_length=50)


def _validate_tracking_event(data: TrackingEventRequest) -> None:
    if data.event_type not in VALID_EVENT_TYPES:
        raise BadRequestException(f"Invalid event type: {data.event_type}. Must be one of: {', '.join(VALID_EVENT_TYPES)}")
    if not data.session_id or len(data.session_id) > 255:
        raise BadRequestException("session_id is required and must be <= 255 characters")
    if data.revenue is not None and data.revenue < 0:
        raise BadRequestException("revenue must be >= 0")
    if data.extra_data and len(str(data.extra_data)) > 10000:
        raise BadRequestException("extra_data must be <= 10KB")


def _create_event(campaign, data: TrackingEventRequest, occurred_at: datetime) -> TrackingEvent:
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


def _parse_occurred_at(data: TrackingEventRequest) -> datetime:
    if data.occurred_at:
        try:
            return datetime.fromisoformat(data.occurred_at.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


@router.post("/events/{tracking_key}")
async def track_event(
    tracking_key: str,
    data: TrackingEventRequest,
    db: AsyncSession = Depends(get_db),
):
    _validate_tracking_event(data)

    result = await db.execute(
        select(Campaign).where(Campaign.tracking_key == tracking_key)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign not found")

    occurred_at = _parse_occurred_at(data)

    # Check deduplication for PURCHASE events
    if data.event_type == "PURCHASE" and data.external_event_id:
        existing = await db.execute(
            select(TrackingEvent).where(
                TrackingEvent.campaign_id == campaign.id,
                TrackingEvent.external_event_id == data.external_event_id,
            )
        )
        if existing.scalar_one_or_none():
            raise BadRequestException("Duplicate event: external_event_id already recorded")

    event = _create_event(campaign, data, occurred_at)
    db.add(event)
    await db.flush()

    return {"status": "ok", "event_id": str(event.id)}


@router.post("/batch/{tracking_key}")
async def track_events_batch(
    tracking_key: str,
    data: TrackingBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.tracking_key == tracking_key)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign not found")

    events = []
    for event_data in data.events:
        _validate_tracking_event(event_data)
        occurred_at = _parse_occurred_at(event_data)
        event = _create_event(campaign, event_data, occurred_at)
        events.append(event)

    db.add_all(events)
    await db.flush()

    return {"status": "ok", "events_accepted": len(events)}
