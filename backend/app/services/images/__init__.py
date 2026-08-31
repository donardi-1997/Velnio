from app.core.config import settings


def get_image_provider():
    if settings.IMAGE_PROVIDER == "openai":
        from app.services.images.openai_provider import OpenAIImageProvider
        return OpenAIImageProvider()
    from app.services.images.mock_provider import MockImageProvider
    return MockImageProvider()
