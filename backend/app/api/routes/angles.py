"""Compatibility shim for product-scoped Campaign angles endpoints."""

from app.modules.campaigns.api.product_scope import angles_router as router

__all__ = ["router"]
