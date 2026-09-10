"""Add Meta Ads OAuth connection storage.

Revision ID: 012_meta_ads_oauth
Revises: 011_shopify_oauth
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "012_meta_ads_oauth"
down_revision = "011_shopify_oauth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_ads_connections",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.String(length=1024), nullable=False),
        sa.Column("meta_user_id", sa.String(length=255), nullable=False),
        sa.Column("meta_user_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meta_ads_connections_workspace_id", "meta_ads_connections", ["workspace_id"], unique=False)
    op.create_index("ix_meta_ads_connections_user_id", "meta_ads_connections", ["user_id"], unique=False)
    op.create_index("ix_meta_ads_connections_is_active", "meta_ads_connections", ["is_active"], unique=False)

    op.create_table(
        "meta_ads_oauth_states",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nonce_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meta_ads_oauth_states_workspace_id", "meta_ads_oauth_states", ["workspace_id"], unique=False)
    op.create_index("ix_meta_ads_oauth_states_user_id", "meta_ads_oauth_states", ["user_id"], unique=False)
    op.create_index("ix_meta_ads_oauth_states_nonce_hash", "meta_ads_oauth_states", ["nonce_hash"], unique=True)
    op.create_index("ix_meta_ads_oauth_states_expires_at", "meta_ads_oauth_states", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_meta_ads_oauth_states_expires_at", table_name="meta_ads_oauth_states")
    op.drop_index("ix_meta_ads_oauth_states_nonce_hash", table_name="meta_ads_oauth_states")
    op.drop_index("ix_meta_ads_oauth_states_user_id", table_name="meta_ads_oauth_states")
    op.drop_index("ix_meta_ads_oauth_states_workspace_id", table_name="meta_ads_oauth_states")
    op.drop_table("meta_ads_oauth_states")

    op.drop_index("ix_meta_ads_connections_is_active", table_name="meta_ads_connections")
    op.drop_index("ix_meta_ads_connections_user_id", table_name="meta_ads_connections")
    op.drop_index("ix_meta_ads_connections_workspace_id", table_name="meta_ads_connections")
    op.drop_table("meta_ads_connections")
