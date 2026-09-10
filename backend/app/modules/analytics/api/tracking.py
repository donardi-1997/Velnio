from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.db.session import get_db
from app.modules.analytics.application.tracking import TrackingService

router = APIRouter()


class TrackingEventRequest(BaseModel):
    event_type: str
    session_id: str = Field(..., max_length=255)
    visitor_id: Optional[str] = Field(None, max_length=255)
    landing_variant_id: Optional[UUID] = None
    source: Optional[str] = Field(None, max_length=50)
    medium: Optional[str] = Field(None, max_length=50)
    campaign_source: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=2)
    device_type: Optional[str] = Field(None, max_length=20)
    referrer: Optional[str] = Field(None, max_length=2048)
    extra_data: Optional[Dict[str, Any]] = None
    revenue: Optional[float] = None
    currency: Optional[str] = Field(None, max_length=3)
    external_event_id: Optional[str] = Field(None, max_length=255)
    occurred_at: Optional[str] = None


class TrackingBatchRequest(BaseModel):
    events: List[TrackingEventRequest] = Field(..., max_length=50)


def get_tracking_service(db: AsyncSession = Depends(get_db)) -> TrackingService:
    return TrackingService(db)


def _reject_public_purchase(event_type: str) -> None:
    if event_type == "PURCHASE":
        raise BadRequestException(
            "Purchase events can only be recorded by a verified commerce webhook"
        )


@router.post("/events/{tracking_key}")
async def track_event(
    tracking_key: str,
    data: TrackingEventRequest,
    service: TrackingService = Depends(get_tracking_service),
):
    _reject_public_purchase(data.event_type)
    event = await service.track(tracking_key, data)
    return {"status": "ok", "event_id": str(event.id)}


@router.post("/batch/{tracking_key}")
async def track_events_batch(
    tracking_key: str,
    data: TrackingBatchRequest,
    service: TrackingService = Depends(get_tracking_service),
):
    for event in data.events:
        _reject_public_purchase(event.event_type)
    accepted = await service.track_batch(tracking_key, data.events)
    return {"status": "ok", "events_accepted": accepted}


@router.post("/beacon/{tracking_key}", status_code=204, include_in_schema=False)
async def track_storefront_beacon(
    tracking_key: str,
    event_type: str = Form(...),
    session_id: str = Form(..., max_length=255),
    visitor_id: Optional[str] = Form(None, max_length=255),
    landing_variant_id: Optional[UUID] = Form(None),
    source: Optional[str] = Form(None, max_length=50),
    medium: Optional[str] = Form(None, max_length=50),
    campaign_source: Optional[str] = Form(None, max_length=100),
    device_type: Optional[str] = Form(None, max_length=20),
    referrer: Optional[str] = Form(None, max_length=2048),
    occurred_at: Optional[str] = Form(None),
    service: TrackingService = Depends(get_tracking_service),
):
    _reject_public_purchase(event_type)
    await service.track(
        tracking_key,
        TrackingEventRequest(
            event_type=event_type,
            session_id=session_id,
            visitor_id=visitor_id,
            landing_variant_id=landing_variant_id,
            source=source,
            medium=medium,
            campaign_source=campaign_source,
            device_type=device_type,
            referrer=referrer,
            occurred_at=occurred_at,
        ),
    )
    return Response(status_code=204)
