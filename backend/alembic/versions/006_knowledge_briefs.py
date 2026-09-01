"""knowledge sources and campaign briefs

Revision ID: 006
Revises: 005
Create Date: 2026-08-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'knowledge_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False, index=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('content_text', sa.Text, nullable=True),
        sa.Column('url', sa.String(1024), nullable=True),
        sa.Column('source_document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('product_source_documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('imported_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_primary', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'campaign_briefs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False, index=True),
        sa.Column('product_summary', sa.Text, nullable=True),
        sa.Column('target_audience', sa.Text, nullable=True),
        sa.Column('key_benefits', sa.Text, nullable=True),
        sa.Column('tone_of_voice', sa.String(255), nullable=True),
        sa.Column('pricing_strategy', sa.String(255), nullable=True),
        sa.Column('positioning', sa.Text, nullable=True),
        sa.Column('generated_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('credit_cost', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('campaign_briefs')
    op.drop_table('knowledge_sources')
