"""Compatibility shim for campaign publishing routes.

New code should import from ``app.modules.campaigns.api.publishing``.
"""

from app.modules.campaigns.api.publishing import publish_readiness, router

__all__ = ["router", "publish_readiness"]
