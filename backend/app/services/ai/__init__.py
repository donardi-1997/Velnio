from app.core.config import settings
from app.core.exceptions import BadGatewayException


def get_ai_provider():
    if settings.AI_PROVIDER == "openai":
        from app.services.ai.openai_provider import OpenAIProvider

        return OpenAIProvider()
    if settings.AI_PROVIDER == "mock":
        from app.services.ai.mock_provider import MockAIProvider

        return MockAIProvider()
    raise BadGatewayException("AI provider configuration is invalid")
