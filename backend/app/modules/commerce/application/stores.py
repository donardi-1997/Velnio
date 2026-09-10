from uuid import UUID

from app.core.config import settings
from app.core.encryption import encrypt_value
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.store import Store, StoreStatus
from app.modules.billing.application.entitlements import EntitlementService
from app.modules.billing.infrastructure.repository import BillingRepository
from app.modules.commerce.infrastructure.repository import StoreRepository
from app.schemas.store import MockStoreConnect


class StoreService:
    def __init__(self, repository: StoreRepository) -> None:
        self.repository = repository
        self.entitlements = EntitlementService(BillingRepository(repository.db))

    async def list(self, workspace_id: UUID):
        return await self.repository.list_for_workspace(workspace_id)

    async def mock_connect(self, data: MockStoreConnect, workspace_id: UUID) -> Store:
        if settings.SHOPIFY_MODE != "mock":
            raise BadRequestException("Mock Shopify connections are disabled")
        await self.entitlements.assert_can_add_store(workspace_id)
        store = Store(
            workspace_id=workspace_id,
            name=data.name,
            shop_domain=data.shop_domain,
            country=data.country,
            currency=data.currency,
            status=StoreStatus.CONNECTED,
            access_token_encrypted=encrypt_value("mock_token"),
        )
        return await self.repository.add(store)

    async def disconnect(self, store_id: UUID, workspace_id: UUID) -> Store:
        store = await self.repository.get_for_workspace(store_id, workspace_id)
        if store is None:
            raise NotFoundException("Store")
        store.status = StoreStatus.DISCONNECTED
        store.access_token_encrypted = None
        store.refresh_token_encrypted = None
        store.token_expires_at = None
        store.refresh_token_expires_at = None
        store.granted_scopes = None
        return await self.repository.flush_and_refresh(store)
