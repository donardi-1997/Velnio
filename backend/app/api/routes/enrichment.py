"""Compatibility shim for the modular Catalog enrichment API."""

from app.modules.catalog.api.enrichment import router

__all__ = ["router"]
