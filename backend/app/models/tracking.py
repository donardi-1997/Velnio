import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, Text, Float, DateTime, Index, UniqueConstraint, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin


class EventType(str, enum.Enum):
    PAGE_VIEW = "PAGE_VIEW"
    PRODUCT_VIEW = "PRODUCT_VIEW"
    CTA_CLICK = "CTA_CLICK"
    ADD_TO_CART = "ADD_TO_CART"
    BEGIN_CHECKOUT = "BEGIN_CHECKOUT"
    PURCHASE = "PURCHASE"


VALID_EVENT_TYPES = {e.value for e in EventType}


class TrackingEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tracking_events"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    landing_variant_id = Column(UUID(as_uuid=True), ForeignKey("landing_variants.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    visitor_id = Column(String(255), nullable=True, index=True)
    source = Column(String(50), nullable=True)
    medium = Column(String(50), nullable=True)
    campaign_source = Column(String(100), nullable=True)
    country = Column(String(2), nullable=True)
    device_type = Column(String(20), nullable=True)
    referrer = Column(String(2048), nullable=True)
    extra_data = Column("metadata", JSON, nullable=True)
    revenue = Column(Float, nullable=True)
    currency = Column(String(3), nullable=True)
    external_event_id = Column(String(255), nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)

    campaign = relationship("Campaign", back_populates="tracking_events")
    variant = relationship("LandingVariant", back_populates="tracking_events")

    __table_args__ = (
        UniqueConstraint("campaign_id", "external_event_id", name="uq_tracking_external_event"),
    )


class LandingVariantStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


class LandingVariant(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "landing_variants"

    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    variant_key = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default="DRAFT")
    traffic_weight = Column(Float, nullable=False, default=0)
    source_variant_id = Column(UUID(as_uuid=True), ForeignKey("landing_variants.id", ondelete="SET NULL"), nullable=True)
    selling_angle_id = Column(UUID(as_uuid=True), ForeignKey("selling_angles.id", ondelete="SET NULL"), nullable=True)
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", ondelete="SET NULL"), nullable=True)
    landing_page_id = Column(UUID(as_uuid=True), ForeignKey("landing_pages.id", ondelete="SET NULL"), nullable=True)

    campaign = relationship("Campaign", back_populates="variants")
    source_variant = relationship("LandingVariant", remote_side="LandingVariant.id", backref="cloned_variants")
    selling_angle = relationship("SellingAngle")
    offer = relationship("Offer")
    landing_page = relationship("LandingPage", foreign_keys="[LandingVariant.landing_page_id]")
    tracking_events = relationship("TrackingEvent", back_populates="variant")

    __table_args__ = (
        UniqueConstraint("campaign_id", "variant_key", name="uq_variant_key_per_campaign"),
    )


class CampaignPerformanceInsight(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "campaign_performance_insights"

    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    summary = Column(Text, nullable=False, default="")
    winning_pattern = Column(Text, nullable=True)
    weak_points = Column(JSON, nullable=True, default=list)
    recommended_actions = Column(JSON, nullable=True, default=list)
    next_test_type = Column(String(50), nullable=True)
    next_test_hypothesis = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    based_on_sessions = Column(Integer, nullable=False, default=0)
    generated_at = Column(DateTime(timezone=True), nullable=False)

    campaign = relationship("Campaign", back_populates="performance_insights")
