import httpx
import pytest

from app.core.config import settings
from app.core.exceptions import BadRequestException, ForbiddenException
from app.models.workspace import MemberRole, WorkspaceMember
from app.modules.commerce.api.stores import require_store_admin
from app.modules.commerce.application.shopify_connection import ShopifyConnectionService
from app.modules.commerce.application.stores import StoreService
from app.schemas.store import MockStoreConnect
from app.services.shopify.real_provider import RealShopifyProvider


class _RepositoryStub:
    db = None


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
