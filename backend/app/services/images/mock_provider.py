import hashlib
from typing import Any, Dict, Optional
from app.services.images.base import ImageGenerationProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


class MockImageProvider(ImageGenerationProvider):
    async def generate_product_image(
        self, product: Any, purpose: str, prompt: str, visual_direction: Optional[Any] = None
    ) -> Dict[str, Any]:
        product_id = str(getattr(product, "id", "unknown"))
        h = hashlib.md5(f"{product_id}:{purpose}:{prompt}".encode()).hexdigest()[:12]
        logger.info(f"[mock] Generating product image purpose={purpose} hash={h}")
        return {
            "image_url": f"/storage/mock/{purpose}_{h}.png",
            "width": 1024,
            "height": 1024,
        }

    async def generate_lifestyle_image(
        self, product: Any, campaign: Any, angle: str, visual_direction: Optional[Any] = None
    ) -> Dict[str, Any]:
        product_id = str(getattr(product, "id", "unknown"))
        h = hashlib.md5(f"{product_id}:lifestyle:{angle}".encode()).hexdigest()[:12]
        logger.info(f"[mock] Generating lifestyle image angle={angle} hash={h}")
        return {
            "image_url": f"/storage/mock/lifestyle_{h}.png",
            "width": 1200,
            "height": 628,
        }

    async def generate_problem_solution_image(
        self, product: Any, campaign: Any, angle: str, visual_direction: Optional[Any] = None
    ) -> Dict[str, Any]:
        product_id = str(getattr(product, "id", "unknown"))
        h = hashlib.md5(f"{product_id}:problem_solution:{angle}".encode()).hexdigest()[:12]
        logger.info(f"[mock] Generating problem/solution image angle={angle} hash={h}")
        return {
            "image_url": f"/storage/mock/problem_solution_{h}.png",
            "width": 1200,
            "height": 628,
        }

    async def generate_campaign_asset(
        self, product: Any, campaign: Any, angle: str, offer: str, visual_direction: Optional[Any] = None, purpose: str = "HERO"
    ) -> Dict[str, Any]:
        product_id = str(getattr(product, "id", "unknown"))
        h = hashlib.md5(f"{product_id}:{purpose}:{angle}:{offer}".encode()).hexdigest()[:12]
        logger.info(f"[mock] Generating campaign asset purpose={purpose} hash={h}")
        return {
            "image_url": f"/storage/mock/{purpose}_{h}.png",
            "width": 1200,
            "height": 628,
        }
