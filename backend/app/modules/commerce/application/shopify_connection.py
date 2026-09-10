from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Mapping
from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import decrypt_value, encrypt_value
from app.core.exceptions import BadGatewayException, BadRequestException
from app.core.logging import get_logger
from app.core.security import ALGORITHM
from app.models.store import ShopifyOAuthState, Store, StoreStatus
from app.models.user import User
from app.models.workspace import MemberRole, Workspace, WorkspaceMember
from app.modules.billing.application.entitlements import EntitlementService
from app.modules.billing.infrastructure.repository import BillingRepository
from app.modules.commerce.infrastructure.repository import StoreRepository
from app.services.shopify import get_shopify_provider

logger = get_logger(__name__)

SHOPIFY_STATE_TYPE = "shopify_oauth_state"
SHOPIFY_STATE_TTL_MINUTES = 10
TOKEN_REFRESH_SKEW_SECONDS = 300


class ShopifyConnectionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = StoreRepository(db)
        self.entitlements = EntitlementService(BillingRepository(db))

    async def start(self, workspace_id: UUID, user_id: UUID, shop_domain: str) -> dict:
        provider = get_shopify_provider()
        if settings.SHOPIFY_MODE != "real":
            raise BadRequestException("Real Shopify OAuth is not enabled")

        shop = provider._normalize_shop_domain(shop_domain)
        await self._lock_workspace(workspace_id)
        existing = await self.repository.get_by_shop_domain(workspace_id, shop)
        if existing is None or existing.status == StoreStatus.DISCONNECTED:
            await self.entitlements.assert_can_add_store(workspace_id)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=SHOPIFY_STATE_TTL_MINUTES)
        nonce = secrets.token_urlsafe(32)
        self.db.add(
            ShopifyOAuthState(
                workspace_id=workspace_id,
                user_id=user_id,
                shop_domain=shop,
                nonce_hash=self._hash_nonce(nonce),
                expires_at=expires_at,
            )
        )
        await self.db.flush()

        state = jwt.encode(
            {
                "type": SHOPIFY_STATE_TYPE,
                "workspace_id": str(workspace_id),
                "sub": str(user_id),
                "shop": shop,
                "nonce": nonce,
                "iat": now,
                "exp": expires_at,
            },
            settings.JWT_SECRET,
            algorithm=ALGORITHM,
        )
        return {"auth_url": provider.get_install_url(shop, state)}

    async def complete(self, query_params: Mapping[str, str]) -> Store:
        provider = get_shopify_provider()
        if settings.SHOPIFY_MODE != "real":
            raise BadRequestException("Real Shopify OAuth is not enabled")

        provider.verify_callback_hmac(query_params)
        state = query_params.get("state", "")
        callback_shop = provider._normalize_shop_domain(query_params.get("shop", ""))
        code = query_params.get("code", "")
        workspace_id, user_id, state_shop = await self._consume_state(state)
        if callback_shop != state_shop:
            raise BadRequestException("Invalid Shopify OAuth callback")

        await self._lock_workspace(workspace_id)
        existing = await self.repository.get_by_shop_domain(workspace_id, callback_shop)
        if existing is None or existing.status == StoreStatus.DISCONNECTED:
            await self.entitlements.assert_can_add_store(workspace_id)

        try:
            token_data = await provider.exchange_code(code, callback_shop)
            self._validate_required_scopes(token_data.get("scope", ""))
            access_token = self._require_token(token_data, "access_token")
            refresh_token = self._require_token(token_data, "refresh_token")
            expires_in = self._positive_int(token_data, "expires_in")
            refresh_expires_in = self._positive_int(token_data, "refresh_token_expires_in")
            shop_data = await provider.get_shop(access_token, callback_shop)
        except (BadRequestException, BadGatewayException):
            raise
        except Exception as exc:
            logger.warning("Shopify OAuth completion failed: %s", type(exc).__name__)
            raise BadGatewayException("Shopify connection failed; try again") from exc

        now = datetime.now(timezone.utc).replace(microsecond=0)
        store = existing or Store(workspace_id=workspace_id, name=shop_data.get("name") or callback_shop)
        store.name = str(shop_data.get("name") or callback_shop)[:255]
        store.shop_domain = callback_shop
        store.country = str(shop_data.get("country_code") or "US")[:2].upper()
        store.currency = str(shop_data.get("currency") or "USD")[:3].upper()
        store.access_token_encrypted = encrypt_value(access_token)
        store.refresh_token_encrypted = encrypt_value(refresh_token)
        store.token_expires_at = now + timedelta(seconds=expires_in)
        store.refresh_token_expires_at = now + timedelta(seconds=refresh_expires_in)
        store.granted_scopes = str(token_data.get("scope") or "")[:1024]
        store.status = StoreStatus.CONNECTED

        if existing is None:
            self.db.add(store)
        await self.db.flush()
        await self.db.refresh(store)
        return store

    async def ensure_valid_credentials(self, store: Store | None) -> Store | None:
        if store is None or settings.SHOPIFY_MODE != "real":
            return store
        if store.status != StoreStatus.CONNECTED:
            raise BadRequestException("Shopify store not connected. Please connect your store first.")
        if store.token_expires_at is None:
            return store

        expiry = store.token_expires_at
        now = datetime.now(timezone.utc) if expiry.tzinfo is not None else datetime.now()
        if expiry > now + timedelta(seconds=TOKEN_REFRESH_SKEW_SECONDS):
            return store

        refresh_expiry = store.refresh_token_expires_at
        refresh_now = datetime.now(timezone.utc) if refresh_expiry and refresh_expiry.tzinfo is not None else datetime.now()
        if refresh_expiry is not None and refresh_expiry <= refresh_now:
            store.status = StoreStatus.ERROR
            await self.db.flush()
            raise BadRequestException("Shopify authorization expired; reconnect your store")
        if not store.refresh_token_encrypted:
            store.status = StoreStatus.ERROR
            await self.db.flush()
            raise BadRequestException("Shopify authorization expired; reconnect your store")

        try:
            refresh_token = decrypt_value(store.refresh_token_encrypted)
            data = await get_shopify_provider().refresh_access_token(refresh_token, store.shop_domain or "")
            access_token = self._require_token(data, "access_token")
            next_refresh = self._require_token(data, "refresh_token")
            expires_in = self._positive_int(data, "expires_in")
            refresh_expires_in = self._positive_int(data, "refresh_token_expires_in")
            self._validate_required_scopes(data.get("scope", store.granted_scopes or ""))
        except BadRequestException:
            store.status = StoreStatus.ERROR
            await self.db.flush()
            raise
        except BadGatewayException:
            raise
        except Exception as exc:
            logger.warning("Shopify token refresh failed: %s", type(exc).__name__)
            raise BadGatewayException("Shopify token refresh failed; try again") from exc

        refreshed_at = datetime.now(timezone.utc).replace(microsecond=0)
        store.access_token_encrypted = encrypt_value(access_token)
        store.refresh_token_encrypted = encrypt_value(next_refresh)
        store.token_expires_at = refreshed_at + timedelta(seconds=expires_in)
        store.refresh_token_expires_at = refreshed_at + timedelta(seconds=refresh_expires_in)
        store.granted_scopes = str(data.get("scope") or store.granted_scopes or "")[:1024]
        await self.db.flush()
        return store

    async def _consume_state(self, state: str) -> tuple[UUID, UUID, str]:
        try:
            payload = jwt.decode(
                state,
                settings.JWT_SECRET,
                algorithms=[ALGORITHM],
                options={"require": ["type", "workspace_id", "sub", "shop", "nonce", "iat", "exp"]},
            )
        except jwt.InvalidTokenError as exc:
            raise BadRequestException("Invalid or expired Shopify OAuth state") from exc
        if payload.get("type") != SHOPIFY_STATE_TYPE:
            raise BadRequestException("Invalid or expired Shopify OAuth state")

        try:
            workspace_id = UUID(payload["workspace_id"])
            user_id = UUID(payload["sub"])
            shop = str(payload["shop"])
            nonce = str(payload["nonce"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BadRequestException("Invalid or expired Shopify OAuth state") from exc
        if not nonce or not shop:
            raise BadRequestException("Invalid or expired Shopify OAuth state")

        result = await self.db.execute(
            select(ShopifyOAuthState)
            .where(
                ShopifyOAuthState.workspace_id == workspace_id,
                ShopifyOAuthState.user_id == user_id,
                ShopifyOAuthState.shop_domain == shop,
                ShopifyOAuthState.nonce_hash == self._hash_nonce(nonce),
            )
            .with_for_update()
        )
        stored = result.scalar_one_or_none()
        if stored is None or stored.consumed_at is not None:
            raise BadRequestException("Invalid or expired Shopify OAuth state")
        expiry = stored.expires_at
        now = datetime.now(timezone.utc) if expiry.tzinfo is not None else datetime.now()
        if expiry <= now:
            raise BadRequestException("Invalid or expired Shopify OAuth state")

        user = (await self.db.execute(select(User).where(User.id == user_id, User.is_active == True))).scalar_one_or_none()
        membership = (
            await self.db.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if (
            user is None
            or membership is None
            or membership.role not in {MemberRole.OWNER, MemberRole.ADMIN}
        ):
            raise BadRequestException("Shopify OAuth authorization is no longer valid")

        stored.consumed_at = now
        await self.db.flush()
        return workspace_id, user_id, shop

    async def _lock_workspace(self, workspace_id: UUID) -> None:
        workspace = (
            await self.db.execute(select(Workspace).where(Workspace.id == workspace_id).with_for_update())
        ).scalar_one_or_none()
        if workspace is None:
            raise BadRequestException("Workspace not found")

    @staticmethod
    def _hash_nonce(nonce: str) -> str:
        return hashlib.sha256(nonce.encode("utf-8")).hexdigest()

    @staticmethod
    def _require_token(data: dict, key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise BadGatewayException("Shopify did not return valid credentials")
        return value

    @staticmethod
    def _positive_int(data: dict, key: str) -> int:
        try:
            value = int(data.get(key))
        except (TypeError, ValueError) as exc:
            raise BadGatewayException("Shopify did not return valid credentials") from exc
        if value <= 0:
            raise BadGatewayException("Shopify did not return valid credentials")
        return value

    @staticmethod
    def _scope_is_granted(required_scope: str, granted: set[str]) -> bool:
        if required_scope in granted:
            return True
        if required_scope.startswith("read_"):
            matching_write_scope = f"write_{required_scope[5:]}"
            return matching_write_scope in granted
        return False

    @classmethod
    def _validate_required_scopes(cls, scope_value: str) -> None:
        granted = {item.strip() for item in str(scope_value).split(",") if item.strip()}
        required = {item.strip() for item in settings.SHOPIFY_SCOPES.split(",") if item.strip()}
        missing = {scope for scope in required if not cls._scope_is_granted(scope, granted)}
        if missing:
            raise BadRequestException("Shopify did not grant all required permissions; reconnect your store")
