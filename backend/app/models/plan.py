from sqlalchemy import Column, String, Float, Integer, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin


class Plan(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "plans"

    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    monthly_price = Column(Float, nullable=False, default=0)
    included_credits = Column(Integer, nullable=False, default=0)
    max_stores = Column(Integer, nullable=False, default=1)
    max_products_per_month = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)

    subscriptions = relationship("Subscription", back_populates="plan")
