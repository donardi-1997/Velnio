"""google drive integration

Revision ID: 005_google_drive
Revises: 004_tracking_variants_experiments
Create Date: 2024-05-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '005_google_drive'
down_revision: Union[str, None] = '004_tracking_variants_experiments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # CREATE google_drive_connections table
    op.create_table(
        'google_drive_connections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False, index=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('access_token_encrypted', sa.Text, nullable=False),
        sa.Column('refresh_token_encrypted', sa.Text, nullable=False),
        sa.Column('token_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scope', sa.String(512), nullable=False),
        sa.Column('google_email', sa.String(255), nullable=True),
        sa.Column('google_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # CREATE product_source_documents table
    op.create_table(
        'product_source_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False, index=True),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('external_file_id', sa.String(255), nullable=False),
        sa.Column('external_file_name', sa.String(512), nullable=True),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('file_size', sa.Integer, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='IMPORTED'),
        sa.Column('storage_key', sa.String(512), nullable=True),
        sa.Column('content_text', sa.Text, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('imported_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ALTER product_images: add Google Drive fields
    op.add_column('product_images', sa.Column('external_source', sa.String(50), nullable=True))
    op.add_column('product_images', sa.Column('external_file_id', sa.String(255), nullable=True))
    op.add_column('product_images', sa.Column('external_file_name', sa.String(512), nullable=True))
    op.add_column('product_images', sa.Column('storage_key', sa.String(512), nullable=True))
    op.add_column('product_images', sa.Column('purpose', sa.String(50), nullable=False, server_default='ORIGINAL'))

    # Add unique constraint for idempotent imports
    op.create_index('uq_product_image_external', 'product_images', ['product_id', 'external_source', 'external_file_id'], unique=True, postgresql_where='external_source IS NOT NULL AND external_file_id IS NOT NULL')


def downgrade() -> None:
    op.drop_index('uq_product_image_external', table_name='product_images')
    op.drop_column('product_images', 'purpose')
    op.drop_column('product_images', 'storage_key')
    op.drop_column('product_images', 'external_file_name')
    op.drop_column('product_images', 'external_file_id')
    op.drop_column('product_images', 'external_source')

    op.drop_table('product_source_documents')
    op.drop_table('google_drive_connections')
