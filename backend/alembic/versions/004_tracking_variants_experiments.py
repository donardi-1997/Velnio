"""tracking, variants, experiments, performance insights

Revision ID: 004_tracking_variants_experiments
Revises: 003_enrichment_visual_assets
Create Date: 2024-04-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = '004_tracking_variants_experiments'
down_revision: Union[str, None] = '003_enrichment_visual_assets'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ALTER campaigns: add tracking_key
    op.add_column('campaigns', sa.Column('tracking_key', sa.String(64), nullable=True, unique=True, index=True))

    # ALTER offers: add status, remove unique constraint on campaign_id
    op.add_column('offers', sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE'))
    op.alter_column('offers', 'status', server_default=None)

    # Drop the unique constraint on offers.campaign_id
    op.execute("ALTER TABLE offers DROP CONSTRAINT IF EXISTS offers_campaign_id_key")

    # ALTER landing_pages: add variant_id
    op.add_column('landing_pages', sa.Column('variant_id', UUID(as_uuid=True), sa.ForeignKey('landing_variants.id', ondelete='SET NULL'), nullable=True, index=True))

    # CREATE landing_variants table
    op.create_table(
        'landing_variants',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('variant_key', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='DRAFT'),
        sa.Column('traffic_weight', sa.Float, nullable=False, server_default='0'),
        sa.Column('source_variant_id', UUID(as_uuid=True), sa.ForeignKey('landing_variants.id', ondelete='SET NULL'), nullable=True),
        sa.Column('selling_angle_id', UUID(as_uuid=True), sa.ForeignKey('selling_angles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('offer_id', UUID(as_uuid=True), sa.ForeignKey('offers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('landing_page_id', UUID(as_uuid=True), sa.ForeignKey('landing_pages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('campaign_id', 'variant_key', name='uq_variant_key_per_campaign'),
    )

    # CREATE tracking_events table
    op.create_table(
        'tracking_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False, index=True),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('landing_variant_id', UUID(as_uuid=True), sa.ForeignKey('landing_variants.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('event_type', sa.String(50), nullable=False, index=True),
        sa.Column('session_id', sa.String(255), nullable=False, index=True),
        sa.Column('visitor_id', sa.String(255), nullable=True, index=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('medium', sa.String(50), nullable=True),
        sa.Column('campaign_source', sa.String(100), nullable=True),
        sa.Column('country', sa.String(2), nullable=True),
        sa.Column('device_type', sa.String(20), nullable=True),
        sa.Column('referrer', sa.String(2048), nullable=True),
        sa.Column('metadata', JSON, nullable=True),
        sa.Column('revenue', sa.Float, nullable=True),
        sa.Column('currency', sa.String(3), nullable=True),
        sa.Column('external_event_id', sa.String(255), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('campaign_id', 'external_event_id', name='uq_tracking_external_event'),
    )

    # CREATE campaign_performance_insights table
    op.create_table(
        'campaign_performance_insights',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('summary', sa.Text, nullable=False, server_default=''),
        sa.Column('winning_pattern', sa.Text, nullable=True),
        sa.Column('weak_points', JSON, nullable=True),
        sa.Column('recommended_actions', JSON, nullable=True),
        sa.Column('next_test_type', sa.String(50), nullable=True),
        sa.Column('next_test_hypothesis', sa.Text, nullable=True),
        sa.Column('confidence', sa.Float, nullable=True),
        sa.Column('based_on_sessions', sa.Integer, nullable=False, server_default='0'),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('campaign_performance_insights')
    op.drop_table('tracking_events')
    op.drop_table('landing_variants')

    op.drop_column('landing_pages', 'variant_id')
    op.drop_column('offers', 'status')
    op.drop_column('campaigns', 'tracking_key')
