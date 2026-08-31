import uuid
from sqlalchemy import Column, String, ForeignKey, Text, Float, Integer, Boolean, DateTime, Enum as SAEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin
import enum


class CampaignStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ANALYZING = "ANALYZING"
    ANGLE_READY = "ANGLE_READY"
    LANDING_READY = "LANDING_READY"
    READY = "READY"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class Campaign(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=True, index=True)
    name = Column(String(512), nullable=False)
    status = Column(SAEnum(CampaignStatus, name="campaign_status", create_constraint=True), nullable=False, default=CampaignStatus.DRAFT, index=True)
    target_country = Column(String(2), nullable=False, default="US")
    target_language = Column(String(10), nullable=False, default="en")
    currency = Column(String(3), nullable=False, default="USD")
    selling_price = Column(Float, nullable=True)
    supplier_price = Column(Float, nullable=True)
    target_audience = Column(String(255), nullable=True)
    payment_strategy = Column(String(100), nullable=True)
    shipping_strategy = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    external_product_id = Column(String(255), nullable=True)
    external_page_id = Column(String(255), nullable=True)
    external_page_handle = Column(String(255), nullable=True)
    external_page_url = Column(String(1024), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    last_publish_error = Column(Text, nullable=True)
    tracking_key = Column(String(64), unique=True, nullable=True, index=True)

    workspace = relationship("Workspace", back_populates="campaigns")
    product = relationship("Product", back_populates="campaigns")
    store = relationship("Store", back_populates="campaigns")
    angles = relationship("SellingAngle", back_populates="campaign", cascade="all, delete-orphan", order_by="SellingAngle.position", lazy="selectin")
    landing_page = relationship("LandingPage", back_populates="campaign", uselist=False, cascade="all, delete-orphan")
    offer = relationship("Offer", back_populates="campaign", cascade="all, delete-orphan")
    visual_direction = relationship("CampaignVisualDirection", back_populates="campaign", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    images = relationship("ProductImage", back_populates="campaign", cascade="all, delete-orphan", lazy="selectin")
    variants = relationship("LandingVariant", back_populates="campaign", cascade="all, delete-orphan", lazy="selectin")
    source_documents = relationship("ProductSourceDocument", back_populates="campaign", cascade="all, delete-orphan", lazy="selectin")
    tracking_events = relationship("TrackingEvent", back_populates="campaign", cascade="all, delete-orphan")
    performance_insights = relationship("CampaignPerformanceInsight", back_populates="campaign", cascade="all, delete-orphan")
