import warnings

from sqlalchemy.exc import SAWarning

import app.models  # noqa: F401 - load all model metadata
from app.db.base import Base
from app.models.google_drive import ProductSourceDocument
from app.models.landing import LandingPage
from app.models.tracking import LandingVariant


def test_landing_variant_owns_landing_page_relationship() -> None:
    assert "variant_id" not in LandingPage.__table__.columns

    variant_targets = {
        fk.target_fullname
        for fk in LandingVariant.__table__.c.landing_page_id.foreign_keys
    }
    assert variant_targets == {"landing_pages.id"}

    landing_targets = {
        fk.target_fullname
        for column in LandingPage.__table__.columns
        for fk in column.foreign_keys
    }
    assert "landing_variants.id" not in landing_targets


def test_model_metadata_has_no_unsortable_foreign_key_cycle() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", SAWarning)
        sorted_tables = list(Base.metadata.sorted_tables)

    assert sorted_tables


def test_product_source_document_schema_matches_extraction_model() -> None:
    columns = set(ProductSourceDocument.__table__.columns.keys())
    assert {
        "extracted_text",
        "extraction_error",
        "page_count",
        "character_count",
        "processed_at",
    }.issubset(columns)
    assert "error_message" not in columns
