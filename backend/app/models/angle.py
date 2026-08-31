from sqlalchemy import Column, String, ForeignKey, Text, Float, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin


class SellingAngle(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "selling_angles"

    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    target_audience = Column(String(255), nullable=False)
    pain_point = Column(Text, nullable=False)
    main_promise = Column(Text, nullable=False)
    hook = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    score = Column(Float, nullable=False, default=0)
    position = Column(Integer, nullable=False, default=0)
    selected = Column(Boolean, nullable=False, default=False)

    campaign = relationship("Campaign", back_populates="angles")
    product = relationship("Product")
