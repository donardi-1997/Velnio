"""add campaigns, offers, migrate angles and landings

Revision ID: 002_campaigns
Revises: 001_initial
Create Date: 2024-02-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import table, column

revision: str = '002_campaigns'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create campaign_status enum
    campaign_status = sa.Enum('DRAFT', 'ANALYZING', 'ANGLE_READY', 'LANDING_READY', 'READY', 'PUBLISHED', 'FAILED', 'ARCHIVED', name='campaign_status')
    campaign_status.create(op.get_bind(), checkfirst=True)

    # Create offer_type enum
    offer_type = sa.Enum('STANDARD', 'DISCOUNT', 'BUNDLE', 'BOGO', 'FREE_SHIPPING', 'COD', 'CUSTOM', name='offer_type')
    offer_type.create(op.get_bind(), checkfirst=True)

    # Create campaigns table
    op.create_table(
        'campaigns',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False, index=True),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('store_id', UUID(as_uuid=True), sa.ForeignKey('stores.id'), nullable=True, index=True),
        sa.Column('name', sa.String(512), nullable=False),
        sa.Column('status', campaign_status, nullable=False, server_default='DRAFT', index=True),
        sa.Column('target_country', sa.String(2), nullable=False, server_default='US'),
        sa.Column('target_language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('selling_price', sa.Float, nullable=True),
        sa.Column('supplier_price', sa.Float, nullable=True),
        sa.Column('target_audience', sa.String(255), nullable=True),
        sa.Column('payment_strategy', sa.String(100), nullable=True),
        sa.Column('shipping_strategy', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('external_product_id', sa.String(255), nullable=True),
        sa.Column('external_page_id', sa.String(255), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_publish_error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create offers table
    op.create_table(
        'offers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('headline', sa.String(512), nullable=False, server_default=''),
        sa.Column('offer_type', offer_type, nullable=False, server_default='STANDARD'),
        sa.Column('primary_price', sa.Float, nullable=True),
        sa.Column('compare_at_price', sa.Float, nullable=True),
        sa.Column('discount_percentage', sa.Float, nullable=True),
        sa.Column('bundle_quantity', sa.Integer, nullable=True),
        sa.Column('free_shipping', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('cash_on_delivery', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('guarantee_days', sa.Integer, nullable=True),
        sa.Column('urgency_text', sa.Text, nullable=True),
        sa.Column('scarcity_text', sa.Text, nullable=True),
        sa.Column('bonus_text', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Add campaign_id to selling_angles (nullable for migration)
    op.add_column('selling_angles', sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=True, index=True))

    # Add campaign_id to landing_pages (nullable for migration)
    op.add_column('landing_pages', sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=True, index=True))

    # Data migration: create default campaigns for existing products
    conn = op.get_bind()
    products_table = table('products',
        column('id', UUID(as_uuid=True)),
        column('workspace_id', UUID(as_uuid=True)),
        column('store_id', UUID(as_uuid=True)),
        column('name', sa.String),
        column('target_country', sa.String),
        column('target_language', sa.String),
        column('currency', sa.String),
        column('selling_price', sa.Float),
        column('supplier_price', sa.Float),
    )
    campaigns_table = table('campaigns',
        column('id', UUID(as_uuid=True)),
        column('workspace_id', UUID(as_uuid=True)),
        column('product_id', UUID(as_uuid=True)),
        column('store_id', UUID(as_uuid=True)),
        column('name', sa.String),
        column('status', sa.String),
        column('target_country', sa.String),
        column('target_language', sa.String),
        column('currency', sa.String),
        column('selling_price', sa.Float),
        column('supplier_price', sa.Float),
    )
    angles_table = table('selling_angles',
        column('id', UUID(as_uuid=True)),
        column('product_id', UUID(as_uuid=True)),
        column('campaign_id', UUID(as_uuid=True)),
    )
    landings_table = table('landing_pages',
        column('id', UUID(as_uuid=True)),
        column('product_id', UUID(as_uuid=True)),
        column('campaign_id', UUID(as_uuid=True)),
    )

    result = conn.execute(products_table.select())
    import uuid as uuid_mod
    for row in result:
        product_id = row[0]
        campaign_id = uuid_mod.uuid4()
        product_name = row[4]
        target_country = row[5]
        target_language = row[6]
        currency = row[7]
        selling_price = row[8]
        supplier_price = row[9]

        # Determine campaign status based on what exists
        has_angle = conn.execute(angles_table.select().where(angles_table.c.product_id == product_id).limit(1)).fetchone()
        has_landing = conn.execute(landings_table.select().where(landings_table.c.product_id == product_id).limit(1)).fetchone()

        if has_landing:
            campaign_status = 'READY'
        elif has_angle:
            campaign_status = 'ANGLE_READY'
        else:
            campaign_status = 'DRAFT'

        campaign_name = f"Default Campaign - {target_country}"
        if has_angle:
            angle_row = conn.execute(angles_table.select().where(angles_table.c.product_id == product_id).limit(1)).fetchone()
            if angle_row:
                campaign_name = f"{target_country} - {angle_row[2] if angle_row[2] else product_name}"

        conn.execute(campaigns_table.insert().values(
            id=campaign_id,
            workspace_id=row[1],
            product_id=product_id,
            store_id=row[2],
            name=campaign_name,
            status=campaign_status,
            target_country=target_country,
            target_language=target_language,
            currency=currency,
            selling_price=selling_price,
            supplier_price=supplier_price,
        ))

        # Move angles to this campaign
        conn.execute(angles_table.update()
            .where(angles_table.c.product_id == product_id)
            .values(campaign_id=campaign_id))

        # Move landings to this campaign
        conn.execute(landings_table.update()
            .where(landings_table.c.product_id == product_id)
            .values(campaign_id=campaign_id))


def downgrade() -> None:
    op.drop_column('landing_pages', 'campaign_id')
    op.drop_column('selling_angles', 'campaign_id')
    op.drop_table('offers')
    op.drop_table('campaigns')
    op.execute("DROP TYPE IF EXISTS offer_type")
    op.execute("DROP TYPE IF EXISTS campaign_status")
