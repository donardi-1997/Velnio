"""Compatibility shim for the modular identity auth routes."""

from app.modules.identity.api.auth import router

__all__ = ["router"]
