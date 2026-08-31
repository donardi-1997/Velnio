from sqlalchemy import Column, String, ForeignKey, Text, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin


class ProductAnalysis(UUIDMixin, Base):
    __tablename__ = "product_analyses"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True)
    overall_score = Column(Float, nullable=False, default=0)
    demand_score = Column(Float, nullable=False, default=0)
    visual_score = Column(Float, nullable=False, default=0)
    problem_score = Column(Float, nullable=False, default=0)
    margin_score = Column(Float, nullable=False, default=0)
    saturation_score = Column(Float, nullable=False, default=0)
    ad_potential_score = Column(Float, nullable=False, default=0)
    impulse_score = Column(Float, nullable=False, default=0)
    return_risk_score = Column(Float, nullable=False, default=0)
    summary = Column(Text, nullable=False, default="")
    strengths = Column(JSON, nullable=False, default=list)
    risks = Column(JSON, nullable=False, default=list)
    recommended_price_min = Column(Float, nullable=True)
    recommended_price_max = Column(Float, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=False)

    product = relationship("Product", back_populates="analysis")
