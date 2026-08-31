from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ImageGenerationProvider(ABC):
    @abstractmethod
    async def generate_product_image(
        self, product: Any, purpose: str, prompt: str, visual_direction: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Generate a product image. Returns dict with image_url, width, height."""
        raise NotImplementedError

    @abstractmethod
    async def generate_lifestyle_image(
        self, product: Any, campaign: Any, angle: str, visual_direction: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Generate a lifestyle/contextual image for a product."""
        raise NotImplementedError

    @abstractmethod
    async def generate_problem_solution_image(
        self, product: Any, campaign: Any, angle: str, visual_direction: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Generate a problem/solution comparison image."""
        raise NotImplementedError

    @abstractmethod
    async def generate_campaign_asset(
        self, product: Any, campaign: Any, angle: str, offer: str, visual_direction: Optional[Any] = None, purpose: str = "HERO"
    ) -> Dict[str, Any]:
        """Generate a campaign-specific image asset."""
        raise NotImplementedError
