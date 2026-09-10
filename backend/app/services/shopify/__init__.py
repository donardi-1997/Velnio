from app.core.config import settings


def get_shopify_provider():
    if settings.SHOPIFY_MODE == "real":
        from app.services.shopify.real_provider import RealShopifyProvider
        return RealShopifyProvider()
    if settings.SHOPIFY_MODE == "mock":
        from app.services.shopify.mock_provider import MockShopifyProvider
        return MockShopifyProvider()
    raise RuntimeError(f"Unsupported SHOPIFY_MODE: {settings.SHOPIFY_MODE}")
