"""Compatibility shim for the modular billing credit routes."""

from app.modules.billing.api.credits import router

__all__ = ["router"]
