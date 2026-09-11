"""Add Meta Ads ad set publication records.

Revision ID: 015_meta_ads_ad_set_publications
Revises: 014_meta_ads_delivery_config
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "015_meta_ads_ad_set_publications"
down_revision = "014_meta_ads_delivery_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_ads_ad_set_publications",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("remote_ad_set_id", sa.String(length=128), nullable=False),
        sa.Column("remote_ad_set_name", sa.String(length=512), nullable=False),
        sa.Column("remote_status", sa.String(length=32), nullable=False),
        sa.Column("target_country", sa.String(length=2), nullable=False),
        sa.Column("daily_budget_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("optimization_goal", sa.String(length=64), nullable=False),
        sa.Column("billing_event", sa.String(length=64), nullable=False),
        sa.Column("bid_strategy", sa.String(length=64), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_publication_id"],
            ["meta_ads_campaign_publications.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("remote_ad_set_id"),
    )
    op.create_index(
        "ix_meta_ads_ad_set_publications_workspace_id",
        "meta_ads_ad_set_publications",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_ad_set_publications_campaign_publication_id",
        "meta_ads_ad_set_publications",
        ["campaign_publication_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meta_ads_ad_set_publications_campaign_publication_id",
        table_name="meta_ads_ad_set_publications",
    )
    op.drop_index(
        "ix_meta_ads_ad_set_publications_workspace_id",
        table_name="meta_ads_ad_set_publications",
    )
    op.drop_table("meta_ads_ad_set_publications")
