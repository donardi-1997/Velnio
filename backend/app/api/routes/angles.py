"""Compatibility shim for product-scoped Campaign angles endpoints."""

from app.modules.campaigns.api.product_scope import router

__all__ = ["router"]
