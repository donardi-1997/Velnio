"""Compatibility shim for product-scoped Campaign landing endpoints."""

from app.modules.campaigns.api.product_scope import router

__all__ = ["router"]
