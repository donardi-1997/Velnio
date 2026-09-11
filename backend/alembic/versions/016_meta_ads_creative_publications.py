"""Add Meta Ads standalone creative publication records.

Revision ID: 016_meta_ads_creative_publications
Revises: 015_meta_ads_ad_set_publications
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "016_meta_ads_creative_publications"
down_revision = "015_meta_ads_ad_set_publications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_ads_creative_publications",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ad_set_publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_image_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("remote_creative_id", sa.String(length=128), nullable=False),
        sa.Column("remote_creative_name", sa.String(length=512), nullable=False),
        sa.Column("destination_url", sa.String(length=2048), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=False),
        sa.Column("primary_text", sa.Text(), nullable=False),
        sa.Column("headline", sa.String(length=255), nullable=True),
        sa.Column("call_to_action", sa.String(length=64), nullable=False),
        sa.Column("page_id", sa.String(length=128), nullable=False),
        sa.Column("instagram_account_id", sa.String(length=128), nullable=True),
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
        sa.ForeignKeyConstraint(["product_image_id"], ["product_images.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
        sa.UniqueConstraint("remote_creative_id"),
    )
    op.create_index(
        "ix_meta_ads_creative_publications_workspace_id",
        "meta_ads_creative_publications",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_creative_publications_campaign_publication_id",
        "meta_ads_creative_publications",
        ["campaign_publication_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_creative_publications_ad_set_publication_id",
        "meta_ads_creative_publications",
        ["ad_set_publication_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_creative_publications_product_image_id",
        "meta_ads_creative_publications",
        ["product_image_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_creative_publications_idempotency_key",
        "meta_ads_creative_publications",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_meta_ads_creative_publications_idempotency_key", table_name="meta_ads_creative_publications")
    op.drop_index("ix_meta_ads_creative_publications_product_image_id", table_name="meta_ads_creative_publications")
    op.drop_index("ix_meta_ads_creative_publications_ad_set_publication_id", table_name="meta_ads_creative_publications")
    op.drop_index("ix_meta_ads_creative_publications_campaign_publication_id", table_name="meta_ads_creative_publications")
    op.drop_index("ix_meta_ads_creative_publications_workspace_id", table_name="meta_ads_creative_publications")
    op.drop_table("meta_ads_creative_publications")
