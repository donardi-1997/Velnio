from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID

import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import decrypt_value, encrypt_value
from app.core.exceptions import BadRequestException, ForbiddenException
from app.core.logging import get_logger
from app.core.security import ALGORITHM
from app.models.meta_ads import MetaAdsConnection, MetaAdsOAuthState
from app.models.user import User
from app.models.workspace import MemberRole, Workspace, WorkspaceMember
from app.modules.integrations.infrastructure.meta_ads import MetaAdsProviderError, get_meta_ads_provider


logger = get_logger(__name__)
OAUTH_STATE_TYPE = "meta_ads_oauth_state"
OAUTH_STATE_TTL_MINUTES = 10


class MetaAdsConnectionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active_connection(self, workspace_id: UUID) -> MetaAdsConnection | None:
        result = await self.db.execute(
            select(MetaAdsConnection)
            .where(
                MetaAdsConnection.workspace_id == workspace_id,
                MetaAdsConnection.is_active == True,
            )
            .order_by(MetaAdsConnection.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def status(self, workspace_id: UUID) -> dict:
        connection = await self.get_active_connection(workspace_id)
        if connection is None:
            return {"connected": False, "expired": False}
        expired = self._is_expired(connection.token_expires_at)
        return {
            "connected": True,
            "expired": expired,
            "meta_user_id": connection.meta_user_id,
            "meta_user_name": connection.meta_user_name,
            "connected_at": connection.created_at,
            "expires_at": connection.token_expires_at,
        }

    async def auth_url(self, workspace_id: UUID, user_id: UUID) -> dict:
        await self._require_admin_membership(workspace_id, user_id)
        provider = get_meta_ads_provider()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=OAUTH_STATE_TTL_MINUTES)
        nonce = secrets.token_urlsafe(32)
        state_record = MetaAdsOAuthState(
            workspace_id=workspace_id,
            user_id=user_id,
            nonce_hash=self._hash_nonce(nonce),
            expires_at=expires_at,
        )
        self.db.add(state_record)
        await self.db.flush()
        state = jwt.encode(
            {
                "type": OAUTH_STATE_TYPE,
                "workspace_id": str(workspace_id),
                "sub": str(user_id),
                "nonce": nonce,
                "iat": now,
                "exp": expires_at,
            },
            settings.JWT_SECRET,
            algorithm=ALGORITHM,
        )
        try:
            auth_url = await provider.get_auth_url(state)
        except MetaAdsProviderError as exc:
            raise BadRequestException(str(exc)) from exc
        return {"auth_url": auth_url, "mode": settings.META_ADS_MODE}

    async def validate_oauth_state(self, state: str) -> tuple[UUID, UUID]:
        try:
            payload = jwt.decode(
                state,
                settings.JWT_SECRET,
                algorithms=[ALGORITHM],
                options={"require": ["type", "workspace_id", "sub", "nonce", "iat", "exp"]},
            )
        except jwt.InvalidTokenError as exc:
            raise BadRequestException("Invalid or expired Meta Ads OAuth state") from exc
        if payload.get("type") != OAUTH_STATE_TYPE:
            raise BadRequestException("Invalid or expired Meta Ads OAuth state")
        nonce = payload.get("nonce")
        if not isinstance(nonce, str) or not nonce:
            raise BadRequestException("Invalid or expired Meta Ads OAuth state")
        try:
            workspace_id = UUID(payload["workspace_id"])
            user_id = UUID(payload["sub"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BadRequestException("Invalid or expired Meta Ads OAuth state") from exc

        result = await self.db.execute(
            select(MetaAdsOAuthState)
            .where(
                MetaAdsOAuthState.workspace_id == workspace_id,
                MetaAdsOAuthState.user_id == user_id,
                MetaAdsOAuthState.nonce_hash == self._hash_nonce(nonce),
            )
            .with_for_update()
        )
        record = result.scalar_one_or_none()
        if record is None or record.consumed_at is not None:
            raise BadRequestException("Invalid or expired Meta Ads OAuth state")
        expiry = record.expires_at
        now = datetime.now(timezone.utc) if expiry.tzinfo is not None else datetime.now()
        if expiry <= now:
            raise BadRequestException("Invalid or expired Meta Ads OAuth state")

        user_result = await self.db.execute(select(User).where(User.id == user_id, User.is_active == True))
        if user_result.scalar_one_or_none() is None:
            raise BadRequestException("Meta Ads OAuth user is no longer active")
        await self._require_admin_membership(workspace_id, user_id)
        record.consumed_at = now
        await self.db.flush()
        return workspace_id, user_id

    async def connect_from_code(self, workspace_id: UUID, user_id: UUID, code: str) -> MetaAdsConnection:
        provider = get_meta_ads_provider()
        try:
            token_data = await provider.exchange_code(code)
            access_token = self._require_access_token(token_data)
            profile = await provider.get_profile(access_token)
        except MetaAdsProviderError as exc:
            logger.warning("Meta Ads OAuth exchange failed: %s", type(exc).__name__)
            raise BadRequestException("Failed to authenticate with Meta Ads; start the connection again") from exc
        return await self._replace_connection(workspace_id, user_id, token_data, profile)

    async def connect_mock(self, workspace_id: UUID, user_id: UUID) -> dict:
        if settings.APP_ENV.lower() == "production" or settings.META_ADS_MODE.lower() != "mock":
            raise ForbiddenException("Mock Meta Ads connections are disabled")
        await self._require_admin_membership(workspace_id, user_id)
        provider = get_meta_ads_provider()
        token_data = await provider.exchange_code("mock_code")
        access_token = self._require_access_token(token_data)
        profile = await provider.get_profile(access_token)
        connection = await self._replace_connection(workspace_id, user_id, token_data, profile)
        return {
            "connected": True,
            "meta_user_id": connection.meta_user_id,
            "meta_user_name": connection.meta_user_name,
        }

    async def disconnect(self, workspace_id: UUID, user_id: UUID) -> dict:
        await self._require_admin_membership(workspace_id, user_id)
        await self.db.execute(
            update(MetaAdsConnection)
            .where(
                MetaAdsConnection.workspace_id == workspace_id,
                MetaAdsConnection.is_active == True,
            )
            .values(is_active=False)
        )
        await self.db.flush()
        return {"disconnected": True}

    async def list_ad_accounts(self, workspace_id: UUID) -> list[dict]:
        access_token = await self.get_valid_token(workspace_id)
        provider = get_meta_ads_provider()
        try:
            return await provider.list_ad_accounts(access_token)
        except MetaAdsProviderError as exc:
            logger.warning("Meta Ads account discovery failed: %s", type(exc).__name__)
            raise BadRequestException("Could not load Meta ad accounts") from exc

    async def get_valid_token(self, workspace_id: UUID) -> str:
        connection = await self.get_active_connection(workspace_id)
        if connection is None:
            raise BadRequestException("Meta Ads not connected")
        if self._is_expired(connection.token_expires_at):
            raise BadRequestException("Meta Ads access expired; reconnect Meta Ads")
        try:
            token = decrypt_value(connection.access_token_encrypted)
        except Exception as exc:
            logger.warning("Meta Ads token decryption failed: %s", type(exc).__name__)
            raise BadRequestException("Meta Ads credentials are invalid; reconnect Meta Ads") from exc
        if not token:
            raise BadRequestException("Meta Ads credentials are invalid; reconnect Meta Ads")
        return token

    async def _replace_connection(
        self,
        workspace_id: UUID,
        user_id: UUID,
        token_data: dict,
        profile: dict,
    ) -> MetaAdsConnection:
        access_token = self._require_access_token(token_data)
        meta_user_id = profile.get("id")
        if not isinstance(meta_user_id, str) or not meta_user_id:
            raise BadRequestException("Meta returned an invalid user profile")

        workspace_result = await self.db.execute(
            select(Workspace).where(Workspace.id == workspace_id).with_for_update()
        )
        if workspace_result.scalar_one_or_none() is None:
            raise BadRequestException("Workspace not found")
        await self.db.execute(
            update(MetaAdsConnection)
            .where(
                MetaAdsConnection.workspace_id == workspace_id,
                MetaAdsConnection.is_active == True,
            )
            .values(is_active=False)
        )
        expires_in = self._expires_in(token_data)
        connection = MetaAdsConnection(
            workspace_id=workspace_id,
            user_id=user_id,
            access_token_encrypted=encrypt_value(access_token),
            token_expires_at=datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=expires_in),
            scopes=str(token_data.get("scope") or settings.META_ADS_SCOPES),
            meta_user_id=meta_user_id,
            meta_user_name=profile.get("name") if isinstance(profile.get("name"), str) else None,
            is_active=True,
        )
        self.db.add(connection)
        await self.db.flush()
        await self.db.refresh(connection)
        return connection

    async def _require_admin_membership(self, workspace_id: UUID, user_id: UUID) -> WorkspaceMember:
        result = await self.db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None or member.role not in {MemberRole.OWNER, MemberRole.ADMIN}:
            raise ForbiddenException("Owner or admin role required for Meta Ads")
        return member

    @staticmethod
    def _hash_nonce(nonce: str) -> str:
        return hashlib.sha256(nonce.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_expired(expires_at: datetime | None) -> bool:
        if expires_at is None:
            return True
        now = datetime.now(timezone.utc) if expires_at.tzinfo is not None else datetime.now()
        return expires_at <= now

    @staticmethod
    def _require_access_token(token_data: dict) -> str:
        token = token_data.get("access_token")
        if not isinstance(token, str) or not token:
            raise BadRequestException("Meta did not provide an access token")
        return token

    @staticmethod
    def _expires_in(token_data: dict) -> int:
        try:
            expires_in = int(token_data.get("expires_in", 0))
        except (TypeError, ValueError) as exc:
            raise BadRequestException("Meta returned an invalid token expiry") from exc
        if expires_in <= 0:
            raise BadRequestException("Meta returned an invalid token expiry")
        return expires_in
