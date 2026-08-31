from sqlalchemy import Column, String, ForeignKey, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin
from datetime import datetime, timezone


class CampaignVisualDirection(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "campaign_visual_directions"

    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    visual_style = Column(String(255), nullable=False)
    tone = Column(String(255), nullable=False)
    color_notes = Column(Text, nullable=True)
    background_style = Column(String(255), nullable=True)
    photography_style = Column(String(255), nullable=True)
    audience_context = Column(Text, nullable=True)
    additional_instructions = Column(Text, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    campaign = relationship("Campaign", back_populates="visual_direction")
