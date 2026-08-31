"""enrichment, visual assets, image purposes, product source metadata

Revision ID: 003_enrichment_visual_assets
Revises: 002_campaigns
Create Date: 2024-03-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = '003_enrichment_visual_assets'
down_revision: Union[str, None] = '002_campaigns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Create image_source_type enum
    image_source_type = sa.Enum('SOURCE', 'UPLOADED', 'AI_GENERATED', name='image_source_type')
    image_source_type.create(conn, checkfirst=True)

    # Create image_purpose enum
    image_purpose = sa.Enum(
        'ORIGINAL', 'HERO', 'LIFESTYLE', 'PROBLEM', 'SOLUTION',
        'BENEFIT', 'BEFORE', 'AFTER', 'COMPARISON', 'SOCIAL', 'OTHER',
        name='image_purpose'
    )
    image_purpose.create(conn, checkfirst=True)

    # campaign_status enum already created in 002_campaigns

    # ALTER campaigns: make product_id nullable, add external_page_handle, external_page_url
    op.alter_column('campaigns', 'product_id', nullable=True)
    op.add_column('campaigns', sa.Column('external_page_handle', sa.String(255), nullable=True))
    op.add_column('campaigns', sa.Column('external_page_url', sa.String(1024), nullable=True))

    # ALTER selling_angles: product_id already nullable from 002 migration

    # ALTER landing_pages: product_id already nullable from 002 migration

    # ALTER products: add source metadata columns
    op.add_column('products', sa.Column('source_domain', sa.String(512), nullable=True))
    op.add_column('products', sa.Column('source_external_id', sa.String(255), nullable=True))
    op.add_column('products', sa.Column('source_metadata', JSON, nullable=True))

    # ALTER product_images: add new columns
    op.add_column('product_images', sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='SET NULL'), nullable=True, index=True))
    op.add_column('product_images', sa.Column('source_type', sa.String(50), nullable=False, server_default='SOURCE'))
    op.add_column('product_images', sa.Column('purpose', sa.String(50), nullable=False, server_default='ORIGINAL'))
    op.add_column('product_images', sa.Column('storage_key', sa.String(512), nullable=True))
    op.add_column('product_images', sa.Column('prompt', sa.Text, nullable=True))
    op.add_column('product_images', sa.Column('generation_provider', sa.String(50), nullable=True))
    op.add_column('product_images', sa.Column('generation_model', sa.String(100), nullable=True))
    op.add_column('product_images', sa.Column('width', sa.Integer, nullable=True))
    op.add_column('product_images', sa.Column('height', sa.Integer, nullable=True))
    op.add_column('product_images', sa.Column('selected', sa.Boolean, nullable=False, server_default='false'))

    # Remove server defaults after migration
    op.alter_column('product_images', 'source_type', server_default=None)
    op.alter_column('product_images', 'purpose', server_default=None)
    op.alter_column('product_images', 'selected', server_default=None)

    # CREATE product_enrichments table
    op.create_table(
        'product_enrichments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('features', JSON, nullable=True),
        sa.Column('benefits', JSON, nullable=True),
        sa.Column('use_cases', JSON, nullable=True),
        sa.Column('suggested_audiences', JSON, nullable=True),
        sa.Column('short_description', sa.Text, nullable=True),
        sa.Column('enriched_description', sa.Text, nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # CREATE campaign_visual_directions table
    op.create_table(
        'campaign_visual_directions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), unique=True, nullable=False, index=True),
        sa.Column('visual_style', sa.String(255), nullable=False),
        sa.Column('tone', sa.String(255), nullable=False),
        sa.Column('color_notes', sa.Text, nullable=True),
        sa.Column('background_style', sa.String(255), nullable=True),
        sa.Column('photography_style', sa.String(255), nullable=True),
        sa.Column('audience_context', sa.Text, nullable=True),
        sa.Column('additional_instructions', sa.Text, nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create storage directory
    import os
    os.makedirs("./storage/products", exist_ok=True)
    os.makedirs("./storage/mock", exist_ok=True)


def downgrade() -> None:
    op.drop_table('campaign_visual_directions')
    op.drop_table('product_enrichments')

    op.drop_column('product_images', 'selected')
    op.drop_column('product_images', 'height')
    op.drop_column('product_images', 'width')
    op.drop_column('product_images', 'generation_model')
    op.drop_column('product_images', 'generation_provider')
    op.drop_column('product_images', 'prompt')
    op.drop_column('product_images', 'storage_key')
    op.drop_column('product_images', 'purpose')
    op.drop_column('product_images', 'source_type')
    op.drop_column('product_images', 'campaign_id')

    op.drop_column('products', 'source_metadata')
    op.drop_column('products', 'source_external_id')
    op.drop_column('products', 'source_domain')

    op.drop_column('campaigns', 'external_page_url')
    op.drop_column('campaigns', 'external_page_handle')

    op.execute("DROP TYPE IF EXISTS image_purpose")
    op.execute("DROP TYPE IF EXISTS image_source_type")
