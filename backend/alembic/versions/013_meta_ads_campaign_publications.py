"""Add Meta Ads campaign publication records.

Revision ID: 013_meta_ads_campaign_publications
Revises: 012_meta_ads_oauth
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "013_meta_ads_campaign_publications"
down_revision = "012_meta_ads_oauth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_ads_campaign_publications",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ad_account_id", sa.String(length=64), nullable=False),
        sa.Column("remote_campaign_id", sa.String(length=128), nullable=False),
        sa.Column("remote_campaign_name", sa.String(length=512), nullable=False),
        sa.Column("objective", sa.String(length=64), nullable=False),
        sa.Column("remote_status", sa.String(length=32), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("remote_campaign_id"),
        sa.UniqueConstraint(
            "campaign_id",
            "ad_account_id",
            name="uq_meta_ads_campaign_publication_campaign_account",
        ),
    )
    op.create_index(
        "ix_meta_ads_campaign_publications_workspace_id",
        "meta_ads_campaign_publications",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_campaign_publications_campaign_id",
        "meta_ads_campaign_publications",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_campaign_publications_ad_account_id",
        "meta_ads_campaign_publications",
        ["ad_account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meta_ads_campaign_publications_ad_account_id",
        table_name="meta_ads_campaign_publications",
    )
    op.drop_index(
        "ix_meta_ads_campaign_publications_campaign_id",
        table_name="meta_ads_campaign_publications",
    )
    op.drop_index(
        "ix_meta_ads_campaign_publications_workspace_id",
        table_name="meta_ads_campaign_publications",
    )
    op.drop_table("meta_ads_campaign_publications")
