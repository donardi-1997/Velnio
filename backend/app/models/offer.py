from sqlalchemy import Column, String, ForeignKey, Text, Float, Integer, Boolean, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin
import enum


class OfferType(str, enum.Enum):
    STANDARD = "STANDARD"
    DISCOUNT = "DISCOUNT"
    BUNDLE = "BUNDLE"
    BOGO = "BOGO"
    FREE_SHIPPING = "FREE_SHIPPING"
    COD = "COD"
    CUSTOM = "CUSTOM"


class Offer(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "offers"

    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    headline = Column(String(512), nullable=False, default="")
    status = Column(String(20), nullable=False, default="ACTIVE")
    offer_type = Column(SAEnum(OfferType, name="offer_type", create_constraint=True), nullable=False, default=OfferType.STANDARD)
    primary_price = Column(Float, nullable=True)
    compare_at_price = Column(Float, nullable=True)
    discount_percentage = Column(Float, nullable=True)
    bundle_quantity = Column(Integer, nullable=True)
    free_shipping = Column(Boolean, nullable=False, default=False)
    cash_on_delivery = Column(Boolean, nullable=False, default=False)
    guarantee_days = Column(Integer, nullable=True)
    urgency_text = Column(Text, nullable=True)
    scarcity_text = Column(Text, nullable=True)
    bonus_text = Column(Text, nullable=True)

    campaign = relationship("Campaign", back_populates="offer")
