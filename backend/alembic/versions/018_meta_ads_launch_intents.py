"""Add short-lived Meta Ads launch intents.

Revision ID: 018_meta_ads_launch_intents
Revises: 017_meta_ads_ad_publications
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "018_meta_ads_launch_intents"
down_revision = "017_meta_ads_ad_publications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_ads_launch_intents",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ad_set_publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creative_publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ad_publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("readiness_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["ad_publication_id"],
            ["meta_ads_ad_publications.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meta_ads_launch_intents_workspace_id",
        "meta_ads_launch_intents",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_launch_intents_campaign_publication_id",
        "meta_ads_launch_intents",
        ["campaign_publication_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_launch_intents_ad_set_publication_id",
        "meta_ads_launch_intents",
        ["ad_set_publication_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_launch_intents_creative_publication_id",
        "meta_ads_launch_intents",
        ["creative_publication_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_launch_intents_ad_publication_id",
        "meta_ads_launch_intents",
        ["ad_publication_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_launch_intents_created_by_user_id",
        "meta_ads_launch_intents",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_launch_intents_token_hash",
        "meta_ads_launch_intents",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_meta_ads_launch_intents_readiness_fingerprint",
        "meta_ads_launch_intents",
        ["readiness_fingerprint"],
        unique=False,
    )
    op.create_index(
        "ix_meta_ads_launch_intents_expires_at",
        "meta_ads_launch_intents",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_meta_ads_launch_intents_expires_at", table_name="meta_ads_launch_intents")
    op.drop_index("ix_meta_ads_launch_intents_readiness_fingerprint", table_name="meta_ads_launch_intents")
    op.drop_index("ix_meta_ads_launch_intents_token_hash", table_name="meta_ads_launch_intents")
    op.drop_index("ix_meta_ads_launch_intents_created_by_user_id", table_name="meta_ads_launch_intents")
    op.drop_index("ix_meta_ads_launch_intents_ad_publication_id", table_name="meta_ads_launch_intents")
    op.drop_index("ix_meta_ads_launch_intents_creative_publication_id", table_name="meta_ads_launch_intents")
    op.drop_index("ix_meta_ads_launch_intents_ad_set_publication_id", table_name="meta_ads_launch_intents")
    op.drop_index("ix_meta_ads_launch_intents_campaign_publication_id", table_name="meta_ads_launch_intents")
    op.drop_index("ix_meta_ads_launch_intents_workspace_id", table_name="meta_ads_launch_intents")
    op.drop_table("meta_ads_launch_intents")
