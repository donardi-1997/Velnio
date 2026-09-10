"""add Stripe billing state and webhook idempotency

Revision ID: 010_stripe_billing
Revises: 009_plan_pricing
Create Date: 2026-09-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "010_stripe_billing"
down_revision: Union[str, None] = "009_plan_pricing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("provider_customer_id", sa.String(length=255), nullable=True))
    op.add_column("subscriptions", sa.Column("provider_price_id", sa.String(length=255), nullable=True))
    op.add_column(
        "subscriptions",
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("subscriptions", sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True))
    op.add_column("subscriptions", sa.Column("trial_used_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_subscriptions_provider_subscription_id",
        "subscriptions",
        ["provider_subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscriptions_provider_customer_id",
        "subscriptions",
        ["provider_customer_id"],
        unique=False,
    )

    op.create_table(
        "billing_webhook_events",
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_event_id",
            name="uq_billing_webhook_provider_event",
        ),
    )


def downgrade() -> None:
    op.drop_table("billing_webhook_events")
    op.drop_index("ix_subscriptions_provider_customer_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_provider_subscription_id", table_name="subscriptions")
    op.drop_column("subscriptions", "trial_used_at")
    op.drop_column("subscriptions", "trial_end")
    op.drop_column("subscriptions", "cancel_at_period_end")
    op.drop_column("subscriptions", "provider_price_id")
    op.drop_column("subscriptions", "provider_customer_id")
