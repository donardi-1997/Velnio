from typing import Any, Dict, Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProductEnrichmentService:
    """Enriches product data with features, benefits, use cases, and audience suggestions."""

    async def enrich_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        title = product_data.get("name", "")
        description = product_data.get("description", "")

        if settings.AI_PROVIDER == "mock":
            return self._mock_enrichment(title, description)

        return await self._ai_enrichment(title, description)

    def _mock_enrichment(self, title: str, description: str) -> Dict[str, Any]:
        return {
            "features": [
                "High-quality construction",
                "Modern design",
                "Easy to use",
                "Durable materials",
            ],
            "benefits": [
                "Saves time and effort",
                "Long-lasting value",
                "Improves daily convenience",
                "Professional-grade results",
            ],
            "use_cases": [
                "Daily use at home",
                "Professional settings",
                "Gift for loved ones",
            ],
            "suggested_audiences": [
                "Homeowners",
                "Young professionals",
                "Gift buyers",
            ],
            "short_description": f"{title} - A quality product designed for everyday use.",
            "enriched_description": f"{title} offers exceptional quality and value. {description} Perfect for those seeking reliability and modern design.",
        }

    async def enrich(self, product) -> Dict[str, Any]:
        title = getattr(product, "name", "")
        description = getattr(product, "description", "") or ""
        return await self.enrich_product({"name": title, "description": description})

    async def _ai_enrichment(self, title: str, description: str) -> Dict[str, Any]:
        import httpx

        prompt = f"""Analyze this product and return a JSON object with these fields:
- features: array of 3-5 key product features
- benefits: array of 3-5 customer benefits
- use_cases: array of 2-4 primary use cases
- suggested_audiences: array of 2-3 target audience segments
- short_description: a 1-sentence product summary
- enriched_description: a 2-3 sentence expanded product description

Product title: {title}
Product description: {description}

Return ONLY valid JSON."""

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                json={
                    "model": settings.OPENAI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            import json
            return json.loads(content)
