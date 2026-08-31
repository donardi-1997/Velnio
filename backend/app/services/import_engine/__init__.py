from typing import List
from app.services.import_engine.base import ProductSourceProvider
from app.services.import_engine.ssrf import safe_fetch_url, validate_url, check_ip_not_private
from app.core.config import settings


def get_import_providers() -> List[ProductSourceProvider]:
    from app.services.import_engine.generic_web import GenericWebProvider
    from app.services.import_engine.mock_provider import MockProductProvider

    if settings.AI_PROVIDER == "mock":
        return [MockProductProvider()]
    return [GenericWebProvider()]


async def import_product_from_url(url: str) -> dict:
    """Attempt to import product data from a URL using available providers."""
    validated_url = safe_fetch_url(url)
    if not validated_url:
        from app.core.exceptions import BadRequestException
        raise BadRequestException(f"URL failed security validation: {url}")

    providers = get_import_providers()
    last_error = None

    for provider in providers:
        if not provider.can_handle(validated_url):
            continue
        try:
            normalized = provider.normalize_url(validated_url)
            raw = await provider.fetch_product(normalized)
            data = await provider.extract_product_data(raw)
            data["source_url"] = validated_url
            return data
        except Exception as e:
            last_error = e
            continue

    if last_error:
        raise last_error
    raise ValueError(f"No provider could handle URL: {url}")
