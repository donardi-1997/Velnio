from abc import ABC, abstractmethod
from typing import Any, Dict, Mapping


class ShopifyProvider(ABC):
    @abstractmethod
    def get_install_url(self, shop_domain: str, state: str) -> str:
        pass

    @abstractmethod
    def verify_callback_hmac(self, query_params: Mapping[str, str]) -> None:
        pass

    @abstractmethod
    async def exchange_code(self, code: str, shop_domain: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str, shop_domain: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_shop(self, access_token: str, shop_domain: str = "") -> Dict[str, Any]:
        pass

    @abstractmethod
    async def create_product(
        self,
        access_token: str,
        shop_domain: str,
        product_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def create_page(
        self,
        access_token: str,
        shop_domain: str,
        page_data: Dict[str, Any],
    ) -> Dict[str, Any]:
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
