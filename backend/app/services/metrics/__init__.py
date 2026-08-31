from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.tracking import TrackingEvent


class CampaignMetricsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_campaign_metrics(
        self,
        campaign_id: UUID,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        conditions = [TrackingEvent.campaign_id == campaign_id]
        if from_date:
            conditions.append(TrackingEvent.occurred_at >= from_date)
        if to_date:
            conditions.append(TrackingEvent.occurred_at <= to_date)

        base_query = select(TrackingEvent).where(and_(*conditions))

        # Unique sessions
        sessions_q = await self.db.execute(
            select(func.count(func.distinct(TrackingEvent.session_id))).where(and_(*conditions))
        )
        sessions = sessions_q.scalar() or 0

        # Unique visitors
        visitors_q = await self.db.execute(
            select(func.count(func.distinct(TrackingEvent.visitor_id))).where(
                and_(*conditions, TrackingEvent.visitor_id.isnot(None))
            )
        )
        visitors = visitors_q.scalar() or 0

        # Event counts
        page_views_q = await self.db.execute(
            select(func.count()).where(and_(*conditions, TrackingEvent.event_type == "PAGE_VIEW"))
        )
        page_views = page_views_q.scalar() or 0

        cta_clicks_q = await self.db.execute(
            select(func.count()).where(and_(*conditions, TrackingEvent.event_type == "CTA_CLICK"))
        )
        cta_clicks = cta_clicks_q.scalar() or 0

        add_to_carts_q = await self.db.execute(
            select(func.count()).where(and_(*conditions, TrackingEvent.event_type == "ADD_TO_CART"))
        )
        add_to_carts = add_to_carts_q.scalar() or 0

        checkouts_q = await self.db.execute(
            select(func.count()).where(and_(*conditions, TrackingEvent.event_type == "BEGIN_CHECKOUT"))
        )
        checkouts = checkouts_q.scalar() or 0

        purchases_q = await self.db.execute(
            select(func.count()).where(and_(*conditions, TrackingEvent.event_type == "PURCHASE"))
        )
        purchases = purchases_q.scalar() or 0

        # Revenue
        revenue_q = await self.db.execute(
            select(func.coalesce(func.sum(TrackingEvent.revenue), 0.0)).where(
                and_(*conditions, TrackingEvent.event_type == "PURCHASE", TrackingEvent.revenue.isnot(None))
            )
        )
        revenue = revenue_q.scalar() or 0.0

        # Calculate ratios
        ctr = (cta_clicks / page_views) if page_views > 0 else 0.0
        atc_rate = (add_to_carts / sessions) if sessions > 0 else 0.0
        checkout_rate = (checkouts / sessions) if sessions > 0 else 0.0
        conversion_rate = (purchases / sessions) if sessions > 0 else 0.0
        revenue_per_visitor = (revenue / visitors) if visitors > 0 else 0.0
        aov = (revenue / purchases) if purchases > 0 else 0.0

        return {
            "visitors": visitors,
            "sessions": sessions,
            "page_views": page_views,
            "cta_clicks": cta_clicks,
            "add_to_carts": add_to_carts,
            "checkouts": checkouts,
            "purchases": purchases,
            "revenue": round(revenue, 2),
            "ctr": round(ctr, 4),
            "atc_rate": round(atc_rate, 4),
            "checkout_rate": round(checkout_rate, 4),
            "conversion_rate": round(conversion_rate, 4),
            "revenue_per_visitor": round(revenue_per_visitor, 2),
            "aov": round(aov, 2),
        }

    async def get_campaign_timeline(
        self,
        campaign_id: UUID,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        conditions = [TrackingEvent.campaign_id == campaign_id]
        if from_date:
            conditions.append(TrackingEvent.occurred_at >= from_date)
        if to_date:
            conditions.append(TrackingEvent.occurred_at <= to_date)

        result = await self.db.execute(
            select(
                func.date(TrackingEvent.occurred_at).label("date"),
                func.count().label("total_events"),
                func.count(TrackingEvent.id).filter(TrackingEvent.event_type == "PAGE_VIEW").label("page_views"),
                func.count(TrackingEvent.id).filter(TrackingEvent.event_type == "CTA_CLICK").label("cta_clicks"),
                func.count(TrackingEvent.id).filter(TrackingEvent.event_type == "ADD_TO_CART").label("add_to_carts"),
                func.count(TrackingEvent.id).filter(TrackingEvent.event_type == "BEGIN_CHECKOUT").label("checkouts"),
                func.count(TrackingEvent.id).filter(TrackingEvent.event_type == "PURCHASE").label("purchases"),
                func.coalesce(func.sum(TrackingEvent.revenue).filter(TrackingEvent.event_type == "PURCHASE"), 0.0).label("revenue"),
            ).where(
                and_(*conditions)
            ).group_by(
                func.date(TrackingEvent.occurred_at)
            ).order_by(
                func.date(TrackingEvent.occurred_at)
            )
        )

        timeline = []
        for row in result:
            sessions_q = await self.db.execute(
                select(func.count(func.distinct(TrackingEvent.session_id))).where(
                    and_(
                        TrackingEvent.campaign_id == campaign_id,
                        func.date(TrackingEvent.occurred_at) == row.date,
                    )
                )
            )
            sessions = sessions_q.scalar() or 0
            timeline.append({
                "date": str(row.date),
                "sessions": sessions,
                "page_views": row.page_views,
                "cta_clicks": row.cta_clicks,
                "add_to_carts": row.add_to_carts,
                "checkouts": row.checkouts,
                "purchases": row.purchases,
                "revenue": round(float(row.revenue or 0), 2),
            })

        return timeline

    async def get_variant_metrics(
        self,
        campaign_id: UUID,
        variant_id: Optional[UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        conditions = [TrackingEvent.campaign_id == campaign_id]
        if variant_id:
            conditions.append(TrackingEvent.landing_variant_id == variant_id)
        if from_date:
            conditions.append(TrackingEvent.occurred_at >= from_date)
        if to_date:
            conditions.append(TrackingEvent.occurred_at <= to_date)

        result = await self.db.execute(
            select(
                TrackingEvent.landing_variant_id,
                func.count(func.distinct(TrackingEvent.session_id)).label("sessions"),
                func.count(TrackingEvent.id).filter(TrackingEvent.event_type == "CTA_CLICK").label("cta_clicks"),
                func.count(TrackingEvent.id).filter(TrackingEvent.event_type == "ADD_TO_CART").label("add_to_carts"),
                func.count(TrackingEvent.id).filter(TrackingEvent.event_type == "BEGIN_CHECKOUT").label("checkouts"),
                func.count(TrackingEvent.id).filter(TrackingEvent.event_type == "PURCHASE").label("purchases"),
                func.coalesce(func.sum(TrackingEvent.revenue).filter(TrackingEvent.event_type == "PURCHASE"), 0.0).label("revenue"),
            ).where(
                and_(*conditions)
            ).group_by(
                TrackingEvent.landing_variant_id
            )
        )

        metrics = []
        for row in result:
            sessions = row.sessions or 0
            purchases = row.purchases or 0
            revenue = float(row.revenue or 0)
            metrics.append({
                "variant_id": str(row.landing_variant_id) if row.landing_variant_id else None,
                "sessions": sessions,
                "cta_clicks": row.cta_clicks,
                "add_to_carts": row.add_to_carts,
                "checkouts": row.checkouts,
                "purchases": purchases,
                "revenue": round(revenue, 2),
                "conversion_rate": round((purchases / sessions) if sessions > 0 else 0.0, 4),
                "aov": round((revenue / purchases) if purchases > 0 else 0.0, 2),
            })

        return metrics

    async def get_angle_metrics(
        self,
        campaign_id: UUID,
    ) -> List[Dict[str, Any]]:
        from app.models.angle import SellingAngle
        from app.models.tracking import LandingVariant

        angles_result = await self.db.execute(
            select(SellingAngle).where(SellingAngle.campaign_id == campaign_id)
        )
        angles = angles_result.scalars().all()

        metrics = []
        for angle in angles:
            variant_result = await self.db.execute(
                select(LandingVariant.id).where(
                    LandingVariant.campaign_id == campaign_id,
                    LandingVariant.selling_angle_id == angle.id,
                )
            )
            variant_ids = [v[0] for v in variant_result.fetchall()]

            conditions = [TrackingEvent.campaign_id == campaign_id]
            if variant_ids:
                conditions.append(TrackingEvent.landing_variant_id.in_(variant_ids))

            sessions_q = await self.db.execute(
                select(func.count(func.distinct(TrackingEvent.session_id))).where(and_(*conditions))
            )
            sessions = sessions_q.scalar() or 0

            purchases_q = await self.db.execute(
                select(func.count()).where(and_(*conditions, TrackingEvent.event_type == "PURCHASE"))
            )
            purchases = purchases_q.scalar() or 0

            revenue_q = await self.db.execute(
                select(func.coalesce(func.sum(TrackingEvent.revenue), 0.0)).where(
                    and_(*conditions, TrackingEvent.event_type == "PURCHASE")
                )
            )
            revenue = revenue_q.scalar() or 0.0

            metrics.append({
                "angle_id": str(angle.id),
                "angle_name": angle.name,
                "sessions": sessions,
                "purchases": purchases,
                "revenue": round(float(revenue), 2),
                "conversion_rate": round((purchases / sessions) if sessions > 0 else 0.0, 4),
                "aov": round((float(revenue) / purchases) if purchases > 0 else 0.0, 2),
            })

        return metrics
