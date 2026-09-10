"""persist one-time Google Drive OAuth state

Revision ID: 008_google_drive_oauth_state
Revises: 007_schema_integrity
Create Date: 2026-09-10

Stores only a SHA-256 digest of the OAuth nonce so signed state tokens can be
consumed exactly once without persisting the bearer value itself.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "008_google_drive_oauth_state"
down_revision: Union[str, None] = "007_schema_integrity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "google_drive_oauth_states",
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("nonce_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_google_drive_oauth_states_workspace_id",
        "google_drive_oauth_states",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_google_drive_oauth_states_user_id",
        "google_drive_oauth_states",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_google_drive_oauth_states_nonce_hash",
        "google_drive_oauth_states",
        ["nonce_hash"],
        unique=True,
    )
    op.create_index(
        "ix_google_drive_oauth_states_expires_at",
        "google_drive_oauth_states",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_google_drive_oauth_states_expires_at",
        table_name="google_drive_oauth_states",
    )
    op.drop_index(
        "ix_google_drive_oauth_states_nonce_hash",
        table_name="google_drive_oauth_states",
    )
    op.drop_index(
        "ix_google_drive_oauth_states_user_id",
        table_name="google_drive_oauth_states",
    )
    op.drop_index(
        "ix_google_drive_oauth_states_workspace_id",
        table_name="google_drive_oauth_states",
    )
    op.drop_table("google_drive_oauth_states")
