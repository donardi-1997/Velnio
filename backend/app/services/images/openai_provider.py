import httpx
from typing import Any, Dict, Optional
from app.services.images.base import ImageGenerationProvider
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIImageProvider(ImageGenerationProvider):
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_IMAGE_MODEL
        self.base_url = "https://api.openai.com/v1"

    async def _generate(self, prompt: str, size: str = "1024x1024") -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/images/generations",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "prompt": prompt, "size": size, "n": 1},
            )
            response.raise_for_status()
            data = response.json()
            image_data = data["data"][0]
            url = image_data.get("url") or image_data.get("b64_json")
            width, height = (int(x) for x in size.split("x"))
            return {"image_url": url, "width": width, "height": height}

    async def generate_product_image(
        self, product: Any, purpose: str, prompt: str, visual_direction: Optional[Any] = None
    ) -> Dict[str, Any]:
        logger.info(f"[openai] Generating product image purpose={purpose}")
        return await self._generate(prompt)

    async def generate_lifestyle_image(
        self, product: Any, campaign: Any, angle: str, visual_direction: Optional[Any] = None
    ) -> Dict[str, Any]:
        logger.info(f"[openai] Generating lifestyle image angle={angle}")
        prompt = self._build_lifestyle_prompt(product, campaign, angle, visual_direction)
        return await self._generate(prompt, size="1792x1024")

    async def generate_problem_solution_image(
        self, product: Any, campaign: Any, angle: str, visual_direction: Optional[Any] = None
    ) -> Dict[str, Any]:
        logger.info(f"[openai] Generating problem/solution image angle={angle}")
        prompt = f"A split comparison image showing a problem on the left and the solution with {getattr(product, 'name', 'product')} on the right. {angle}. Clean, modern marketing style."
        return await self._generate(prompt, size="1792x1024")

    async def generate_campaign_asset(
        self, product: Any, campaign: Any, angle: str, offer: str, visual_direction: Optional[Any] = None, purpose: str = "HERO"
    ) -> Dict[str, Any]:
        logger.info(f"[openai] Generating campaign asset purpose={purpose}")
        prompt = self._build_campaign_prompt(product, campaign, angle, offer, visual_direction, purpose)
        return await self._generate(prompt, size="1792x1024")

    def _build_lifestyle_prompt(self, product: Any, campaign: Any, angle: str, visual_direction: Optional[Any]) -> str:
        name = getattr(product, "name", "product")
        style_notes = ""
        if visual_direction:
            style_notes = f" Style: {getattr(visual_direction, 'visual_style', '')}. Tone: {getattr(visual_direction, 'tone', '')}."
        return f"Lifestyle photography of {name} in a real-life setting. Selling angle: {angle}.{style_notes} Professional product photography, natural lighting."

    def _build_campaign_prompt(self, product: Any, campaign: Any, angle: str, offer: str, visual_direction: Optional[Any], purpose: str) -> str:
        name = getattr(product, "name", "product")
        style_notes = ""
        if visual_direction:
            style_notes = f" Style: {getattr(visual_direction, 'visual_style', '')}. Tone: {getattr(visual_direction, 'tone', '')}."
        return f"Marketing {purpose.lower()} image for {name}. Angle: {angle}. Offer: {offer}.{style_notes} Professional advertising imagery, high quality."
