"""Add selected Meta delivery resources to campaign publications.

Revision ID: 014_meta_ads_delivery_config
Revises: 013_meta_ads_campaign_publications
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "014_meta_ads_delivery_config"
down_revision = "013_meta_ads_campaign_publications"
branch_labels = None
depends_on = None

DELIVERY_CONFIG_USER_FK = "fk_meta_pub_delivery_user"


def upgrade() -> None:
    op.add_column(
        "meta_ads_campaign_publications",
        sa.Column("pixel_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "meta_ads_campaign_publications",
        sa.Column("page_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "meta_ads_campaign_publications",
        sa.Column("instagram_account_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "meta_ads_campaign_publications",
        sa.Column("delivery_configured_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "meta_ads_campaign_publications",
        sa.Column("delivery_configured_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        DELIVERY_CONFIG_USER_FK,
        "meta_ads_campaign_publications",
        "users",
        ["delivery_configured_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        DELIVERY_CONFIG_USER_FK,
        "meta_ads_campaign_publications",
        type_="foreignkey",
    )
    op.drop_column("meta_ads_campaign_publications", "delivery_configured_by_user_id")
    op.drop_column("meta_ads_campaign_publications", "delivery_configured_at")
    op.drop_column("meta_ads_campaign_publications", "instagram_account_id")
    op.drop_column("meta_ads_campaign_publications", "page_id")
    op.drop_column("meta_ads_campaign_publications", "pixel_id")
