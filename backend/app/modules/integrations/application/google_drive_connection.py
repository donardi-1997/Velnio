from datetime import datetime, timedelta, timezone
import secrets
from uuid import UUID

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import decrypt_value, encrypt_value
from app.core.exceptions import BadRequestException
from app.core.security import ALGORITHM
from app.models.google_drive import GoogleDriveConnection
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.schemas.google_drive import GoogleDriveStatus
from app.services.google_drive import get_google_drive_provider


OAUTH_STATE_TYPE = "google_drive_oauth_state"
OAUTH_STATE_TTL_MINUTES = 10


class GoogleDriveConnectionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active_connection(self, workspace_id: UUID) -> GoogleDriveConnection | None:
        result = await self.db.execute(
            select(GoogleDriveConnection).where(
                GoogleDriveConnection.workspace_id == workspace_id,
                GoogleDriveConnection.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def require_active_connection(self, workspace_id: UUID) -> GoogleDriveConnection:
        conn = await self.get_active_connection(workspace_id)
        if conn is None:
            raise BadRequestException("Google Drive not connected")
        return conn

    async def status(self, workspace_id: UUID) -> GoogleDriveStatus:
        conn = await self.get_active_connection(workspace_id)
        if conn is None:
            return GoogleDriveStatus(connected=False)
        return GoogleDriveStatus(
            connected=True,
            google_email=conn.google_email,
            google_name=conn.google_name,
            connected_at=conn.created_at,
        )

    async def auth_url(self, workspace_id: UUID, user_id: UUID) -> dict:
        provider = get_google_drive_provider()
        now = datetime.now(timezone.utc)
        state = jwt.encode(
            {
                "type": OAUTH_STATE_TYPE,
                "workspace_id": str(workspace_id),
                "sub": str(user_id),
                "nonce": secrets.token_urlsafe(16),
                "iat": now,
                "exp": now + timedelta(minutes=OAUTH_STATE_TTL_MINUTES),
            },
            settings.JWT_SECRET,
            algorithm=ALGORITHM,
        )
        return {"auth_url": await provider.get_auth_url(state), "state": state}

    async def validate_oauth_state(self, state: str) -> tuple[UUID, UUID]:
        try:
            payload = jwt.decode(state, settings.JWT_SECRET, algorithms=[ALGORITHM])
        except JWTError as exc:
            raise BadRequestException("Invalid or expired Google Drive OAuth state") from exc

        if payload.get("type") != OAUTH_STATE_TYPE:
            raise BadRequestException("Invalid or expired Google Drive OAuth state")

        try:
            workspace_id = UUID(payload["workspace_id"])
            user_id = UUID(payload["sub"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BadRequestException("Invalid or expired Google Drive OAuth state") from exc

        user_result = await self.db.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        if user_result.scalar_one_or_none() is None:
            raise BadRequestException("Google Drive OAuth user is no longer active")

        membership_result = await self.db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        if membership_result.scalar_one_or_none() is None:
            raise BadRequestException("Google Drive OAuth workspace membership is no longer valid")

        return workspace_id, user_id

    async def connect_from_code(self, workspace_id: UUID, user_id: UUID, code: str) -> GoogleDriveConnection:
        provider = get_google_drive_provider()
        try:
            token_data = await provider.exchange_code(code)
        except Exception as exc:
            raise BadRequestException(f"Failed to authenticate with Google Drive: {str(exc)[:200]}")
        return await self._replace_connection(workspace_id, user_id, token_data)

    async def connect_mock(self, workspace_id: UUID, user_id: UUID) -> dict:
        provider = get_google_drive_provider()
        token_data = await provider.exchange_code("mock_code")
        await self._replace_connection(
            workspace_id,
            user_id,
            token_data,
            google_email="demo@gmail.com",
            google_name="Demo User",
        )
        return {"connected": True, "google_email": "demo@gmail.com", "google_name": "Demo User"}

    async def disconnect(self, workspace_id: UUID) -> dict:
        conn = await self.get_active_connection(workspace_id)
        if conn is not None:
            conn.is_active = False
            await self.db.flush()
        return {"disconnected": True}

    async def get_valid_token(self, workspace_id: UUID) -> str:
        conn = await self.require_active_connection(workspace_id)
        provider = get_google_drive_provider()
        access_token = decrypt_value(conn.access_token_encrypted)
        if conn.token_expiry:
            expiry = conn.token_expiry
            now = datetime.now(timezone.utc) if expiry.tzinfo is not None else datetime.now()
            if expiry < now:
                try:
                    refresh_token = decrypt_value(conn.refresh_token_encrypted)
                    if not refresh_token:
                        raise ValueError("Missing refresh token")
                    token_data = await provider.refresh_token(refresh_token)
                    access_token = token_data["access_token"]
                    conn.access_token_encrypted = encrypt_value(access_token)
                    if token_data.get("expires_in"):
                        conn.token_expiry = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(
                            seconds=token_data["expires_in"]
                        )
                    await self.db.flush()
                except Exception as exc:
                    raise BadRequestException(
                        "Google Drive access expired and could not be refreshed; reconnect Google Drive"
                    ) from exc
        return access_token

    async def _replace_connection(
        self,
        workspace_id: UUID,
        user_id: UUID,
        token_data: dict,
        google_email: str | None = None,
        google_name: str | None = None,
    ) -> GoogleDriveConnection:
        existing = await self.get_active_connection(workspace_id)
        previous_refresh_token = None
        if existing is not None:
            existing.is_active = False
            previous_refresh_token = existing.refresh_token_encrypted

        refresh_token = token_data.get("refresh_token")
        refresh_token_encrypted = (
            encrypt_value(refresh_token)
            if refresh_token
            else previous_refresh_token
        )
        if not refresh_token_encrypted:
            raise BadRequestException("Google Drive did not provide a refresh token")

        conn = GoogleDriveConnection(
            workspace_id=workspace_id,
            user_id=user_id,
            access_token_encrypted=encrypt_value(token_data["access_token"]),
            refresh_token_encrypted=refresh_token_encrypted,
            token_expiry=datetime.now(timezone.utc).replace(microsecond=0)
            + timedelta(seconds=token_data.get("expires_in", 3600)),
            scope=token_data.get("scope", settings.GOOGLE_DRIVE_SCOPES),
            google_email=google_email,
            google_name=google_name,
            is_active=True,
        )
        self.db.add(conn)
        await self.db.flush()
        await self.db.refresh(conn)
        return conn
