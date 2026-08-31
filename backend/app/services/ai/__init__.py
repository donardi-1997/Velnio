from app.core.config import settings


def get_ai_provider():
    if settings.AI_PROVIDER == "openai":
        from app.services.ai.openai_provider import OpenAIProvider
        return OpenAIProvider()
    from app.services.ai.mock_provider import MockAIProvider
    return MockAIProvider()
