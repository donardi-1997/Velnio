"""Compatibility shim for the Catalog product API."""

from app.modules.catalog.api.products import router

__all__ = ["router"]
