from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AIProvider(ABC):
    @abstractmethod
    async def analyze_product(self, product) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def generate_selling_angles(self, product) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def generate_selling_angles_for_campaign(self, product, campaign) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def generate_offer(self, product, campaign, analysis, angle) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def generate_landing(self, product, angle, analysis) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def generate_landing_for_campaign(self, product, campaign, angle, analysis, offer) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def regenerate_landing_section(self, section_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def analyze_campaign_performance(
        self,
        campaign,
        metrics: Dict[str, Any],
        variants: List[Dict[str, Any]],
        angles: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        pass
