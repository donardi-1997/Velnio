"""schema integrity hardening

Revision ID: 007_schema_integrity
Revises: 006
Create Date: 2026-09-10

This revision removes the redundant LandingPage -> LandingVariant back-reference,
aligns campaign-centric nullability/indexes, and brings
product_source_documents in line with the current ORM model.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "007_schema_integrity"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # LandingVariant.landing_page_id is the canonical relationship. Keeping a
    # reverse foreign-key column on landing_pages creates a DDL dependency
    # cycle and two competing sources of truth.
    op.drop_column("landing_pages", "variant_id")

    # Campaign-centric landings and angles may exist without a direct product
    # pointer; the campaign remains their primary aggregate owner. The old
    # one-landing-per-product constraint also prevented multiple campaigns for
    # one product from owning independent landing pages.
    op.alter_column(
        "landing_pages",
        "product_id",
        existing_type=UUID(as_uuid=True),
        nullable=True,
    )
    op.drop_constraint(
        "landing_pages_product_id_key",
        "landing_pages",
        type_="unique",
    )
    op.alter_column(
        "selling_angles",
        "product_id",
        existing_type=UUID(as_uuid=True),
        nullable=True,
    )

    # Keep database indexes aligned with the ORM's query paths.
    op.create_index(
        "ix_offers_campaign_id",
        "offers",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_selling_angles_product_id",
        "selling_angles",
        ["product_id"],
        unique=False,
    )

    # Revision 005 shipped an earlier extraction schema. Preserve existing
    # data by renaming the error column and add the fields used by the current
    # ProductSourceDocument model.
    op.alter_column(
        "product_source_documents",
        "error_message",
        new_column_name="extraction_error",
    )
    op.add_column(
        "product_source_documents",
        sa.Column("extracted_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "product_source_documents",
        sa.Column("page_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "product_source_documents",
        sa.Column("character_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "product_source_documents",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("product_source_documents", "processed_at")
    op.drop_column("product_source_documents", "character_count")
    op.drop_column("product_source_documents", "page_count")
    op.drop_column("product_source_documents", "extracted_text")
    op.alter_column(
        "product_source_documents",
        "extraction_error",
        new_column_name="error_message",
    )

    op.drop_index("ix_selling_angles_product_id", table_name="selling_angles")
    op.drop_index("ix_offers_campaign_id", table_name="offers")
    op.alter_column(
        "selling_angles",
        "product_id",
        existing_type=UUID(as_uuid=True),
        nullable=False,
    )
    op.create_unique_constraint(
        "landing_pages_product_id_key",
        "landing_pages",
        ["product_id"],
    )
    op.alter_column(
        "landing_pages",
        "product_id",
        existing_type=UUID(as_uuid=True),
        nullable=False,
    )

    op.add_column(
        "landing_pages",
        sa.Column("variant_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "landing_pages_variant_id_fkey",
        "landing_pages",
        "landing_variants",
        ["variant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_landing_pages_variant_id",
        "landing_pages",
        ["variant_id"],
        unique=False,
    )
