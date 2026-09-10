from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin
import enum


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    PAST_DUE = "PAST_DUE"
    TRIALING = "TRIALING"


class Subscription(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, unique=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    status = Column(SAEnum(SubscriptionStatus, name="subscription_status", create_constraint=True), nullable=False, default=SubscriptionStatus.ACTIVE)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    provider = Column(String(50), nullable=False, default="MOCK")
    provider_subscription_id = Column(String(255), nullable=True, index=True)
    provider_customer_id = Column(String(255), nullable=True, index=True)
    provider_price_id = Column(String(255), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    trial_used_at = Column(DateTime(timezone=True), nullable=True)

    workspace = relationship("Workspace", back_populates="subscription")
    plan = relationship("Plan", back_populates="subscriptions")


class BillingWebhookEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "billing_webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_billing_webhook_provider_event"),
    )

    provider = Column(String(50), nullable=False)
    provider_event_id = Column(String(255), nullable=False)
    event_type = Column(String(120), nullable=False)
