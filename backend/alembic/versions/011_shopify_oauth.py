"""Add Shopify OAuth state and expiring token storage.

Revision ID: 011_shopify_oauth
Revises: 010_stripe_billing
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "011_shopify_oauth"
down_revision = "010_stripe_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("stores", "access_token_encrypted", type_=sa.Text(), existing_type=sa.String(length=1024))
    op.add_column("stores", sa.Column("refresh_token_encrypted", sa.Text(), nullable=True))
    op.add_column("stores", sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("stores", sa.Column("refresh_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("stores", sa.Column("granted_scopes", sa.String(length=1024), nullable=True))

    op.create_table(
        "shopify_oauth_states",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("nonce_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nonce_hash"),
    )
    op.create_index("ix_shopify_oauth_states_workspace_id", "shopify_oauth_states", ["workspace_id"])
    op.create_index("ix_shopify_oauth_states_user_id", "shopify_oauth_states", ["user_id"])
    op.create_index("ix_shopify_oauth_states_shop_domain", "shopify_oauth_states", ["shop_domain"])
    op.create_index("ix_shopify_oauth_states_nonce_hash", "shopify_oauth_states", ["nonce_hash"], unique=True)
    op.create_index("ix_shopify_oauth_states_expires_at", "shopify_oauth_states", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_shopify_oauth_states_expires_at", table_name="shopify_oauth_states")
    op.drop_index("ix_shopify_oauth_states_nonce_hash", table_name="shopify_oauth_states")
    op.drop_index("ix_shopify_oauth_states_shop_domain", table_name="shopify_oauth_states")
    op.drop_index("ix_shopify_oauth_states_user_id", table_name="shopify_oauth_states")
    op.drop_index("ix_shopify_oauth_states_workspace_id", table_name="shopify_oauth_states")
    op.drop_table("shopify_oauth_states")

    op.drop_column("stores", "granted_scopes")
    op.drop_column("stores", "refresh_token_expires_at")
    op.drop_column("stores", "token_expires_at")
    op.drop_column("stores", "refresh_token_encrypted")
    op.alter_column("stores", "access_token_encrypted", type_=sa.String(length=1024), existing_type=sa.Text())
