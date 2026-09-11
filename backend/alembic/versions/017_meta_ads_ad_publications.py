"""Add Meta Ads paused Ad publication records.

Revision ID: 017_meta_ads_ad_publications
Revises: 016_meta_ads_creative_publications
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "017_meta_ads_ad_publications"
down_revision = "016_meta_ads_creative_publications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_ads_ad_publications",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ad_set_publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creative_publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("remote_ad_id", sa.String(length=128), nullable=False),
        sa.Column("remote_ad_name", sa.String(length=512), nullable=False),
        sa.Column("remote_status", sa.String(length=32), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["campaign_publication_id"],
            ["meta_ads_campaign_publications.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ad_set_publication_id"],
            ["meta_ads_ad_set_publications.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["creative_publication_id"],
            ["meta_ads_creative_publications.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("remote_ad_id"),
        sa.UniqueConstraint(
            "ad_set_publication_id",
            "creative_publication_id",
            name="uq_meta_ads_ad_publication_adset_creative",
        ),
    )
    op.create_index(
        "ix_meta_ads_ad_publications_workspace_id",
        "meta_ads_ad_publications",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_ad_publications_campaign_publication_id",
        "meta_ads_ad_publications",
        ["campaign_publication_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_ad_publications_ad_set_publication_id",
        "meta_ads_ad_publications",
        ["ad_set_publication_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_ad_publications_creative_publication_id",
        "meta_ads_ad_publications",
        ["creative_publication_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_ad_publications_idempotency_key",
        "meta_ads_ad_publications",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_meta_ads_ad_publications_idempotency_key", table_name="meta_ads_ad_publications")
    op.drop_index("ix_meta_ads_ad_publications_creative_publication_id", table_name="meta_ads_ad_publications")
    op.drop_index("ix_meta_ads_ad_publications_ad_set_publication_id", table_name="meta_ads_ad_publications")
    op.drop_index("ix_meta_ads_ad_publications_campaign_publication_id", table_name="meta_ads_ad_publications")
    op.drop_index("ix_meta_ads_ad_publications_workspace_id", table_name="meta_ads_ad_publications")
    op.drop_table("meta_ads_ad_publications")
