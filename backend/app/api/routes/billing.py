"""Compatibility shim for the modular billing routes."""

from app.modules.billing.api.subscriptions import router

__all__ = ["router"]
