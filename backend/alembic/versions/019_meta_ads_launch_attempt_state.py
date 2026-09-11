"""Add durable Meta Ads launch attempt lifecycle state.

Revision ID: 019_meta_ads_launch_attempt_state
Revises: 018_meta_ads_launch_intents
"""

from alembic import op
import sqlalchemy as sa


revision = "019_meta_ads_launch_attempt_state"
down_revision = "018_meta_ads_launch_intents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meta_ads_launch_intents",
        sa.Column(
            "activation_status",
            sa.String(length=32),
            server_default="PENDING_CONFIRMATION",
            nullable=False,
        ),
    )
    op.add_column(
        "meta_ads_launch_intents",
        sa.Column("activation_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "meta_ads_launch_intents",
        sa.Column("activation_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "meta_ads_launch_intents",
        sa.Column("last_activation_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_meta_ads_launch_intents_activation_status",
        "meta_ads_launch_intents",
        ["activation_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meta_ads_launch_intents_activation_status",
        table_name="meta_ads_launch_intents",
    )
    op.drop_column("meta_ads_launch_intents", "last_activation_error")
    op.drop_column("meta_ads_launch_intents", "activation_completed_at")
    op.drop_column("meta_ads_launch_intents", "activation_started_at")
    op.drop_column("meta_ads_launch_intents", "activation_status")
