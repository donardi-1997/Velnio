from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.analytics.application.tracking import TrackingService

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
    revenue: Optional[float] = None
    currency: Optional[str] = Field(None, max_length=3)
    external_event_id: Optional[str] = Field(None, max_length=255)
    occurred_at: Optional[str] = None


class TrackingBatchRequest(BaseModel):
    events: List[TrackingEventRequest] = Field(..., max_length=50)


def get_tracking_service(db: AsyncSession = Depends(get_db)) -> TrackingService:
    return TrackingService(db)


@router.post("/events/{tracking_key}")
async def track_event(
    tracking_key: str,
    data: TrackingEventRequest,
    service: TrackingService = Depends(get_tracking_service),
):
    event = await service.track(tracking_key, data)
    return {"status": "ok", "event_id": str(event.id)}


@router.post("/batch/{tracking_key}")
async def track_events_batch(
    tracking_key: str,
    data: TrackingBatchRequest,
    service: TrackingService = Depends(get_tracking_service),
):
    accepted = await service.track_batch(tracking_key, data.events)
    return {"status": "ok", "events_accepted": accepted}
