from sqlalchemy import Column, String, ForeignKey, Text, Integer, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin
import enum


class LandingStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    GENERATING = "GENERATING"
    READY = "READY"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class LandingPage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "landing_pages"

    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
    selling_angle_id = Column(UUID(as_uuid=True), ForeignKey("selling_angles.id"), nullable=True)
    title = Column(String(512), nullable=False, default="")
    slug = Column(String(512), nullable=False, default="")
    status = Column(SAEnum(LandingStatus, name="landing_status", create_constraint=True), nullable=False, default=LandingStatus.DRAFT)
    version = Column(Integer, nullable=False, default=1)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("landing_variants.id", ondelete="SET NULL"), nullable=True, index=True)

    campaign = relationship("Campaign", back_populates="landing_page")
    sections = relationship("LandingSection", back_populates="landing_page", cascade="all, delete-orphan", order_by="LandingSection.position", lazy="selectin")


class LandingSection(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "landing_sections"

    landing_page_id = Column(UUID(as_uuid=True), ForeignKey("landing_pages.id", ondelete="CASCADE"), nullable=False)
    section_type = Column(String(50), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    content = Column(JSON, nullable=False, default=dict)

    landing_page = relationship("LandingPage", back_populates="sections")
