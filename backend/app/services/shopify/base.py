from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ShopifyProvider(ABC):
    @abstractmethod
    def get_install_url(self) -> str:
        pass

    @abstractmethod
    async def handle_callback(self, code: str, shop: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_shop(self, access_token: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def create_product(self, access_token: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def create_page(self, access_token: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def publish_product(self, product, store=None) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def publish_campaign(self, campaign, product, store, angle, landing, offer) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass
