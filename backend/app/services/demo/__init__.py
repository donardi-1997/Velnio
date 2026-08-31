import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tracking import TrackingEvent


class DemoEventGenerator:
    """Generates realistic demo tracking events for testing and demonstration."""

    DEVICES = ["desktop", "mobile", "tablet"]
    SOURCES = ["google", "facebook", "tiktok", "instagram", "direct", "email"]
    MEDIUMS = ["cpc", "social", "organic", "email", "referral", "direct"]
    COUNTRIES = ["US", "GB", "CA", "AU", "DE", "FR", "BR", "MX", "IN", "JP"]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_for_campaign(
        self,
        campaign_id: UUID,
        workspace_id: UUID,
        variant_a_id: Optional[UUID] = None,
        variant_b_id: Optional[UUID] = None,
        variant_a_sessions: int = 500,
        variant_b_sessions: int = 500,
        variant_a_purchases: int = 18,
        variant_b_purchases: int = 31,
        days_back: int = 14,
    ) -> Dict[str, Any]:
        events = []
        now = datetime.now(timezone.utc)

        # Generate Variant A events
        if variant_a_id:
            a_events = self._generate_variant_events(
                campaign_id=campaign_id,
                workspace_id=workspace_id,
                variant_id=variant_a_id,
                sessions=variant_a_sessions,
                purchases=variant_b_purchases,
                days_back=days_back,
                now=now,
                purchase_rate=variant_a_purchases / variant_a_sessions if variant_a_sessions > 0 else 0,
            )
            events.extend(a_events)

        # Generate Variant B events
        if variant_b_id:
            b_events = self._generate_variant_events(
                campaign_id=campaign_id,
                workspace_id=workspace_id,
                variant_id=variant_b_id,
                sessions=variant_b_sessions,
                purchases=variant_b_purchases,
                days_back=days_back,
                now=now,
                purchase_rate=variant_b_purchases / variant_b_sessions if variant_b_sessions > 0 else 0,
            )
            events.extend(b_events)

        # Bulk insert
        self.db.add_all(events)
        await self.db.flush()

        return {
            "total_events": len(events),
            "variant_a_events": len([e for e in events if e.landing_variant_id == variant_a_id]) if variant_a_id else 0,
            "variant_b_events": len([e for e in events if e.landing_variant_id == variant_b_id]) if variant_b_id else 0,
        }

    def _generate_variant_events(
        self,
        campaign_id: UUID,
        workspace_id: UUID,
        variant_id: UUID,
        sessions: int,
        purchases: int,
        days_back: int,
        now: datetime,
        purchase_rate: float = 0.036,
    ) -> List[TrackingEvent]:
        events = []
        cta_rate = 0.25
        atc_rate = 0.12
        checkout_rate = 0.08

        for i in range(sessions):
            session_id = str(uuid.uuid4())
            visitor_id = str(uuid.uuid4())
            session_time = now - timedelta(
                days=random.randint(0, days_back),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            # PAGE_VIEW
            events.append(TrackingEvent(
                workspace_id=workspace_id,
                campaign_id=campaign_id,
                landing_variant_id=variant_id,
                event_type="PAGE_VIEW",
                session_id=session_id,
                visitor_id=visitor_id,
                source=random.choice(self.SOURCES),
                medium=random.choice(self.MEDIUMS),
                country=random.choice(self.COUNTRIES),
                device_type=random.choice(self.DEVICES),
                occurred_at=session_time,
            ))

            # CTA_CLICK
            if random.random() < cta_rate:
                cta_time = session_time + timedelta(seconds=random.randint(5, 60))
                events.append(TrackingEvent(
                    workspace_id=workspace_id,
                    campaign_id=campaign_id,
                    landing_variant_id=variant_id,
                    event_type="CTA_CLICK",
                    session_id=session_id,
                    visitor_id=visitor_id,
                    occurred_at=cta_time,
                ))

                # ADD_TO_CART
                if random.random() < atc_rate:
                    atc_time = cta_time + timedelta(seconds=random.randint(2, 30))
                    events.append(TrackingEvent(
                        workspace_id=workspace_id,
                        campaign_id=campaign_id,
                        landing_variant_id=variant_id,
                        event_type="ADD_TO_CART",
                        session_id=session_id,
                        visitor_id=visitor_id,
                        occurred_at=atc_time,
                    ))

                    # BEGIN_CHECKOUT
                    if random.random() < checkout_rate:
                        checkout_time = atc_time + timedelta(seconds=random.randint(10, 120))
                        events.append(TrackingEvent(
                            workspace_id=workspace_id,
                            campaign_id=campaign_id,
                            landing_variant_id=variant_id,
                            event_type="BEGIN_CHECKOUT",
                            session_id=session_id,
                            visitor_id=visitor_id,
                            occurred_at=checkout_time,
                        ))

                        # PURCHASE
                        if random.random() < purchase_rate:
                            purchase_time = checkout_time + timedelta(seconds=random.randint(5, 60))
                            revenue = round(random.uniform(19.99, 79.99), 2)
                            events.append(TrackingEvent(
                                workspace_id=workspace_id,
                                campaign_id=campaign_id,
                                landing_variant_id=variant_id,
                                event_type="PURCHASE",
                                session_id=session_id,
                                visitor_id=visitor_id,
                                revenue=revenue,
                                currency="USD",
                                occurred_at=purchase_time,
                            ))

        return events

    async def clear_campaign_events(self, campaign_id: UUID) -> int:
        from sqlalchemy import delete
        result = await self.db.execute(
            delete(TrackingEvent).where(TrackingEvent.campaign_id == campaign_id)
        )
        await self.db.flush()
        return result.rowcount
