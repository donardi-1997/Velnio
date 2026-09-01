import uuid
from sqlalchemy import Column, String, ForeignKey, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin


class CampaignBrief(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "campaign_briefs"

    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    product_summary = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    key_benefits = Column(Text, nullable=True)
    tone_of_voice = Column(String(255), nullable=True)
    pricing_strategy = Column(String(255), nullable=True)
    positioning = Column(Text, nullable=True)
    generated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    credit_cost = Column(String(50), nullable=True)

    campaign = relationship("Campaign", back_populates="brief")
    workspace = relationship("Workspace")
    generated_by = relationship("User")
