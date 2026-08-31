from sqlalchemy import Column, String, ForeignKey, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin
from datetime import datetime, timezone


class ProductEnrichment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "product_enrichments"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False)
    features = Column(JSON, nullable=True, default=list)
    benefits = Column(JSON, nullable=True, default=list)
    use_cases = Column(JSON, nullable=True, default=list)
    suggested_audiences = Column(JSON, nullable=True, default=list)
    short_description = Column(Text, nullable=True)
    enriched_description = Column(Text, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="enrichment")
