"""initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(255), nullable=False, server_default=''),
        sa.Column('last_name', sa.String(255), nullable=False, server_default=''),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'workspaces',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('owner_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    member_role = sa.Enum('owner', 'admin', 'member', name='member_role')
    member_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'workspace_members',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', member_role, nullable=False, server_default='member'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    store_platform = sa.Enum('SHOPIFY', name='store_platform')
    store_platform.create(op.get_bind(), checkfirst=True)
    store_status = sa.Enum('DISCONNECTED', 'PENDING', 'CONNECTED', 'ERROR', name='store_status')
    store_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'stores',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('shop_domain', sa.String(512), nullable=True),
        sa.Column('platform', store_platform, nullable=False, server_default='SHOPIFY'),
        sa.Column('access_token_encrypted', sa.String(1024), nullable=True),
        sa.Column('status', store_status, nullable=False, server_default='DISCONNECTED'),
        sa.Column('country', sa.String(2), nullable=False, server_default='US'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    source_type = sa.Enum('MANUAL', 'ALIEXPRESS', 'AMAZON', 'CJ', 'OTHER', name='source_type')
    source_type.create(op.get_bind(), checkfirst=True)
    product_status = sa.Enum('DRAFT', 'ANALYZING', 'ANALYZED', 'READY', 'PUBLISHED', 'FAILED', name='product_status')
    product_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'products',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('store_id', UUID(as_uuid=True), sa.ForeignKey('stores.id'), nullable=True),
        sa.Column('name', sa.String(512), nullable=False),
        sa.Column('source_type', source_type, nullable=False, server_default='MANUAL'),
        sa.Column('source_url', sa.String(1024), nullable=True),
        sa.Column('supplier_price', sa.Float, nullable=True),
        sa.Column('selling_price', sa.Float, nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('target_country', sa.String(2), nullable=False, server_default='US'),
        sa.Column('target_language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('status', product_status, nullable=False, server_default='DRAFT'),
        sa.Column('published_product_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'product_images',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('image_url', sa.String(1024), nullable=False),
        sa.Column('image_type', sa.String(50), nullable=False, server_default='main'),
        sa.Column('position', sa.Integer, nullable=False, server_default='0'),
        sa.Column('generated_by_ai', sa.String(50), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'product_analyses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('overall_score', sa.Float, nullable=False, server_default='0'),
        sa.Column('demand_score', sa.Float, nullable=False, server_default='0'),
        sa.Column('visual_score', sa.Float, nullable=False, server_default='0'),
        sa.Column('problem_score', sa.Float, nullable=False, server_default='0'),
        sa.Column('margin_score', sa.Float, nullable=False, server_default='0'),
        sa.Column('saturation_score', sa.Float, nullable=False, server_default='0'),
        sa.Column('ad_potential_score', sa.Float, nullable=False, server_default='0'),
        sa.Column('impulse_score', sa.Float, nullable=False, server_default='0'),
        sa.Column('return_risk_score', sa.Float, nullable=False, server_default='0'),
        sa.Column('summary', sa.Text, nullable=False, server_default=''),
        sa.Column('strengths', JSON, nullable=False, server_default='[]'),
        sa.Column('risks', JSON, nullable=False, server_default='[]'),
        sa.Column('recommended_price_min', sa.Float, nullable=True),
        sa.Column('recommended_price_max', sa.Float, nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'selling_angles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('target_audience', sa.String(255), nullable=False),
        sa.Column('pain_point', sa.Text, nullable=False),
        sa.Column('main_promise', sa.Text, nullable=False),
        sa.Column('hook', sa.Text, nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('score', sa.Float, nullable=False, server_default='0'),
        sa.Column('position', sa.Integer, nullable=False, server_default='0'),
        sa.Column('selected', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    landing_status = sa.Enum('DRAFT', 'GENERATING', 'READY', 'PUBLISHED', 'FAILED', name='landing_status')
    landing_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'landing_pages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('selling_angle_id', UUID(as_uuid=True), sa.ForeignKey('selling_angles.id'), nullable=True),
        sa.Column('title', sa.String(512), nullable=False, server_default=''),
        sa.Column('slug', sa.String(512), nullable=False, server_default=''),
        sa.Column('status', landing_status, nullable=False, server_default='DRAFT'),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'landing_sections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('landing_page_id', UUID(as_uuid=True), sa.ForeignKey('landing_pages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('section_type', sa.String(50), nullable=False),
        sa.Column('position', sa.Integer, nullable=False, server_default='0'),
        sa.Column('content', JSON, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'plans',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('monthly_price', sa.Float, nullable=False, server_default='0'),
        sa.Column('included_credits', sa.Integer, nullable=False, server_default='0'),
        sa.Column('max_stores', sa.Integer, nullable=False, server_default='1'),
        sa.Column('max_products_per_month', sa.Integer, nullable=False, server_default='0'),
        sa.Column('active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'credit_wallets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False, unique=True),
        sa.Column('balance', sa.Float, nullable=False, server_default='0'),
        sa.Column('lifetime_credits', sa.Float, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    transaction_type = sa.Enum('ALLOCATION', 'USAGE', 'PURCHASE', 'REFUND', 'ADJUSTMENT', name='transaction_type')
    transaction_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'credit_transactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('wallet_id', UUID(as_uuid=True), sa.ForeignKey('credit_wallets.id'), nullable=False),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('transaction_type', transaction_type, nullable=False),
        sa.Column('description', sa.Text, nullable=False, server_default=''),
        sa.Column('reference_type', sa.String(50), nullable=True),
        sa.Column('reference_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    subscription_status = sa.Enum('ACTIVE', 'CANCELED', 'PAST_DUE', 'TRIALING', name='subscription_status')
    subscription_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'subscriptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False, unique=True),
        sa.Column('plan_id', UUID(as_uuid=True), sa.ForeignKey('plans.id'), nullable=False),
        sa.Column('status', subscription_status, nullable=False, server_default='ACTIVE'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('provider', sa.String(50), nullable=False, server_default='MOCK'),
        sa.Column('provider_subscription_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('subscriptions')
    op.drop_table('credit_transactions')
    op.drop_table('credit_wallets')
    op.drop_table('landing_sections')
    op.drop_table('landing_pages')
    op.drop_table('selling_angles')
    op.drop_table('product_analyses')
    op.drop_table('product_images')
    op.drop_table('products')
    op.drop_table('stores')
    op.drop_table('workspace_members')
    op.drop_table('workspaces')
    op.drop_table('users')
    op.drop_table('plans')
    op.execute("DROP TYPE IF EXISTS subscription_status")
    op.execute("DROP TYPE IF EXISTS transaction_type")
    op.execute("DROP TYPE IF EXISTS landing_status")
    op.execute("DROP TYPE IF EXISTS product_status")
    op.execute("DROP TYPE IF EXISTS source_type")
    op.execute("DROP TYPE IF EXISTS store_status")
    op.execute("DROP TYPE IF EXISTS store_platform")
    op.execute("DROP TYPE IF EXISTS member_role")
