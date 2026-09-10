from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import pytest

from app.core.config import settings
from app.core.encryption import encrypt_value
from app.core.exceptions import BadRequestException, ForbiddenException
from app.models.store import Store, StoreStatus
from app.models.workspace import MemberRole, WorkspaceMember
from app.modules.commerce.api.stores import require_store_admin
from app.modules.commerce.application.shopify_connection import ShopifyConnectionService
from app.modules.commerce.application.stores import StoreService
from app.schemas.store import MockStoreConnect
from app.services.shopify.real_provider import RealShopifyProvider


class _RepositoryStub:
    db = None


class _DbStub:
    def __init__(self):
        self.added = []
        self.flush_count = 0

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.flush_count += 1


@pytest.mark.parametrize("role", [MemberRole.OWNER, MemberRole.ADMIN])
def test_store_admin_allows_owner_and_admin(role):
    member = WorkspaceMember(role=role)
    assert require_store_admin(member) is member


def test_store_admin_rejects_regular_member():
    member = WorkspaceMember(role=MemberRole.MEMBER)
    with pytest.raises(ForbiddenException):
        require_store_admin(member)


@pytest.mark.asyncio
async def test_mock_connect_is_disabled_when_shopify_mode_is_real(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "SHOPIFY_MODE", "real")
    service = StoreService(_RepositoryStub())

    with pytest.raises(BadRequestException) as exc_info:
        await service.mock_connect(MockStoreConnect(), workspace_id=None)

    assert exc_info.value.detail == "Mock Shopify connections are disabled"


def test_write_scope_satisfies_matching_read_scope(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        settings,
        "SHOPIFY_SCOPES",
        "read_products,write_products,read_publications,write_publications",
    )

    ShopifyConnectionService._validate_required_scopes(
        "write_products,write_publications"
    )


def test_unrelated_write_scope_does_not_satisfy_read_scope(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "SHOPIFY_SCOPES", "read_products")

    with pytest.raises(BadRequestException):
        ShopifyConnectionService._validate_required_scopes("write_publications")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("existing_status", "expected_capacity_checks"),
    [
        (StoreStatus.DISCONNECTED, 1),
        (StoreStatus.CONNECTED, 0),
        (StoreStatus.ERROR, 0),
    ],
)
async def test_oauth_start_rechecks_capacity_when_reconnecting_disconnected_store(
    existing_status,
    expected_capacity_checks,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "SHOPIFY_MODE", "real")
    db = _DbStub()
    service = ShopifyConnectionService(db)
    existing = Store(
        workspace_id=uuid4(),
        name="Existing",
        shop_domain="existing-shop.myshopify.com",
        status=existing_status,
        country="US",
        currency="USD",
    )

    class Repository:
        async def get_by_shop_domain(self, workspace_id, shop_domain):
            return existing

    class Entitlements:
        def __init__(self):
            self.calls = 0

        async def assert_can_add_store(self, workspace_id):
            self.calls += 1

    class Provider:
        _normalize_shop_domain = staticmethod(RealShopifyProvider._normalize_shop_domain)

        def get_install_url(self, shop_domain, state):
            return f"https://{shop_domain}/admin/oauth/authorize?state={state}"

    async def lock_workspace(workspace_id):
        return None

    entitlements = Entitlements()
    service.repository = Repository()
    service.entitlements = entitlements
    service._lock_workspace = lock_workspace
    monkeypatch.setattr(
        "app.modules.commerce.application.shopify_connection.get_shopify_provider",
        lambda: Provider(),
    )

    await service.start(existing.workspace_id, uuid4(), existing.shop_domain)

    assert entitlements.calls == expected_capacity_checks
    assert len(db.added) == 1


@pytest.mark.asyncio
async def test_refresh_401_requires_reauthorization(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "SHOPIFY_API_KEY", "key")
    monkeypatch.setattr(settings, "SHOPIFY_API_SECRET", "secret")
    monkeypatch.setattr(
        settings,
        "SHOPIFY_REDIRECT_URI",
        "https://app.example.com/api/stores/shopify/callback",
    )

    class UnauthorizedClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, **kwargs):
            request = httpx.Request(method, url)
            return httpx.Response(401, request=request, text="secret upstream body")

    monkeypatch.setattr(
        "app.services.shopify.real_provider.httpx.AsyncClient",
        UnauthorizedClient,
    )

    with pytest.raises(BadRequestException) as exc_info:
        await RealShopifyProvider().refresh_access_token(
            "shprt_secret",
            "valid-shop.myshopify.com",
        )

    assert exc_info.value.detail == "Shopify authorization expired; reconnect your store"
    assert "secret upstream body" not in exc_info.value.detail


@pytest.mark.asyncio
async def test_terminal_refresh_failure_marks_store_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "SHOPIFY_MODE", "real")
    now = datetime.now(timezone.utc)
    store = Store(
        workspace_id=uuid4(),
        name="Refresh Store",
        shop_domain="refresh-store.myshopify.com",
        status=StoreStatus.CONNECTED,
        country="US",
        currency="USD",
        access_token_encrypted=encrypt_value("old-access"),
        refresh_token_encrypted=encrypt_value("old-refresh"),
        token_expires_at=now - timedelta(minutes=1),
        refresh_token_expires_at=now + timedelta(days=30),
        granted_scopes="write_products,write_online_store_pages,write_publications",
    )

    class Provider:
        async def refresh_access_token(self, refresh_token, shop_domain):
            raise BadRequestException("Shopify authorization expired; reconnect your store")

    db = _DbStub()
    service = ShopifyConnectionService(db)
    monkeypatch.setattr(
        "app.modules.commerce.application.shopify_connection.get_shopify_provider",
        lambda: Provider(),
    )

    with pytest.raises(BadRequestException):
        await service.ensure_valid_credentials(store)

    assert store.status == StoreStatus.ERROR
    assert db.flush_count == 1
