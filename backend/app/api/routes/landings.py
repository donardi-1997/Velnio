"""Compatibility shim for product-scoped Campaign landing endpoints."""

from app.modules.campaigns.api.product_scope import landings_router as router

__all__ = ["router"]
