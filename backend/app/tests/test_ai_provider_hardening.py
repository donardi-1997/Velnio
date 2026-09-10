from types import SimpleNamespace

import httpx
import openai
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.exceptions import BadGatewayException
from app.services.ai import get_ai_provider
from app.services.ai.openai_provider import OpenAIProvider


class _CompletionEndpoint:
    def __init__(self, *, content: str | None = None, error: Exception | None = None):
        self.content = content
        self.error = error

    async def create(self, **kwargs):
        if self.error:
            raise self.error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


def _provider_with_completion(*, content: str | None = None, error: Exception | None = None):
    provider = OpenAIProvider.__new__(OpenAIProvider)
    provider.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=_CompletionEndpoint(content=content, error=error)
        )
    )
    return provider


def test_ai_provider_factory_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "opneai")

    with pytest.raises(BadGatewayException) as exc_info:
        get_ai_provider()

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "AI provider configuration is invalid"


def test_openai_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")

    with pytest.raises(BadGatewayException) as exc_info:
        OpenAIProvider()

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "AI provider is not configured"


def test_openai_provider_configures_timeout_and_retry(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "AI_REQUEST_TIMEOUT_SECONDS", 17.5)
    monkeypatch.setattr(openai, "AsyncOpenAI", FakeClient)

    OpenAIProvider()

    assert captured["api_key"] == "test-key"
    assert captured["timeout"] == 17.5
    assert captured["max_retries"] == 1


@pytest.mark.asyncio
async def test_openai_timeout_is_sanitized():
    timeout = openai.APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/test"))
    provider = _provider_with_completion(error=timeout)

    with pytest.raises(BadGatewayException) as exc_info:
        await provider._request_json("test prompt")

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "AI request timed out; try again"


@pytest.mark.asyncio
async def test_openai_invalid_json_is_rejected():
    provider = _provider_with_completion(content="not-json")

    with pytest.raises(BadGatewayException) as exc_info:
        await provider._request_json("test prompt")

    assert exc_info.value.detail == "AI provider returned invalid JSON"


@pytest.mark.asyncio
async def test_openai_empty_choices_are_rejected():
    provider = OpenAIProvider.__new__(OpenAIProvider)

    class EmptyEndpoint:
        async def create(self, **kwargs):
            return SimpleNamespace(choices=[])

    provider.client = SimpleNamespace(
        chat=SimpleNamespace(completions=EmptyEndpoint())
    )

    with pytest.raises(BadGatewayException) as exc_info:
        await provider._request_json("test prompt")

    assert exc_info.value.detail == "AI provider returned an invalid response"


def test_openai_analysis_validation_rejects_out_of_range_scores():
    provider = OpenAIProvider.__new__(OpenAIProvider)
    invalid = {
        "overall_score": 101,
        "demand_score": 5,
        "visual_score": 5,
        "problem_score": 5,
        "margin_score": 5,
        "saturation_score": 5,
        "ad_potential_score": 5,
        "impulse_score": 5,
        "return_risk_score": 5,
        "summary": "Summary",
        "strengths": ["Strength"],
        "risks": ["Risk"],
    }

    with pytest.raises(BadGatewayException):
        provider._validate_analysis(invalid)


def test_openai_landing_validation_rejects_invalid_sections():
    provider = OpenAIProvider.__new__(OpenAIProvider)

    with pytest.raises(BadGatewayException):
        provider._validate_landing(
            {
                "title": "Landing",
                "slug": "landing",
                "sections": [{"section_type": "HERO", "content": "not-an-object"}],
            }
        )


async def _register(client: AsyncClient, email: str) -> tuple[dict, dict]:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Test12345!",
            "first_name": "AI",
            "last_name": "Hardening",
        },
    )
    assert response.status_code == 201
    data = response.json()
    return data, {"Authorization": f"Bearer {data['access_token']}"}


@pytest.mark.asyncio
async def test_product_analysis_provider_failure_does_not_charge_credits(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    _, headers = await _register(client, "ai-analysis-failure@test.com")
    product = await client.post(
        "/api/products",
        json={"name": "Failure Product", "selling_price": 29.99},
        headers=headers,
    )
    assert product.status_code == 201
    product_id = product.json()["id"]

    balance_before = (await client.get("/api/credits", headers=headers)).json()["balance"]

    class FailingProvider:
        async def analyze_product(self, product):
            raise BadGatewayException("AI provider is unavailable; try again")

    monkeypatch.setattr(
        "app.modules.catalog.application.analysis.get_ai_provider",
        lambda: FailingProvider(),
    )

    response = await client.post(f"/api/products/{product_id}/analyze", headers=headers)
    balance_after = (await client.get("/api/credits", headers=headers)).json()["balance"]

    assert response.status_code == 502
    assert response.json()["detail"] == "AI provider is unavailable; try again"
    assert balance_after == balance_before


@pytest.mark.asyncio
async def test_brief_provider_failure_does_not_charge_credits(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    _, headers = await _register(client, "ai-brief-failure@test.com")
    product = await client.post(
        "/api/products",
        json={"name": "Brief Product", "selling_price": 39.99},
        headers=headers,
    )
    assert product.status_code == 201
    product_id = product.json()["id"]
    campaign = await client.post(
        "/api/campaigns",
        json={"product_id": product_id, "name": "Brief Campaign"},
        headers=headers,
    )
    assert campaign.status_code == 201
    campaign_id = campaign.json()["id"]

    balance_before = (await client.get("/api/credits", headers=headers)).json()["balance"]

    class FailingProvider:
        async def generate_campaign_brief(self, product, campaign, knowledge_context):
            raise BadGatewayException("AI request timed out; try again")

    monkeypatch.setattr(
        "app.modules.campaigns.application.briefs.get_ai_provider",
        lambda: FailingProvider(),
    )

    response = await client.post(
        f"/api/campaigns/{campaign_id}/generate-brief",
        headers=headers,
    )
    balance_after = (await client.get("/api/credits", headers=headers)).json()["balance"]

    assert response.status_code == 502
    assert response.json()["detail"] == "AI request timed out; try again"
    assert balance_after == balance_before
