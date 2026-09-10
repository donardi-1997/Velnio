from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, UnauthorizedException
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.models.workspace import MemberRole, Workspace, WorkspaceMember
from app.schemas.auth import TokenResponse, UserLogin, UserRegister


class IdentityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, data: UserRegister) -> TokenResponse:
        result = await self.db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise BadRequestException("Email already registered")

        user = User(email=data.email, password_hash=hash_password(data.password), first_name=data.first_name, last_name=data.last_name)
        self.db.add(user)
        await self.db.flush()

        workspace = Workspace(name=f"{data.first_name}'s Workspace", owner_id=user.id)
        self.db.add(workspace)
        await self.db.flush()
        self.db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=MemberRole.OWNER))

        plan_result = await self.db.execute(select(Plan).where(Plan.code == "FREE"))
        plan = plan_result.scalar_one_or_none()
        if plan:
            now = datetime.now(timezone.utc)
            self.db.add(Subscription(workspace_id=workspace.id, plan_id=plan.id, status=SubscriptionStatus.ACTIVE, current_period_start=now, current_period_end=now, provider="MOCK"))

        wallet = CreditWallet(workspace_id=workspace.id, balance=settings.FREE_CREDITS, lifetime_credits=settings.FREE_CREDITS)
        self.db.add(wallet)
        await self.db.flush()
        self.db.add(CreditTransaction(workspace_id=workspace.id, wallet_id=wallet.id, amount=settings.FREE_CREDITS, transaction_type=TransactionType.ALLOCATION, description="Free credits on registration"))

        return self._tokens(user)

    async def login(self, data: UserLogin) -> TokenResponse:
        result = await self.db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(data.password, user.password_hash):
            raise UnauthorizedException("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedException("Account is disabled")
        return self._tokens(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid refresh token")
        user_id = payload.get("sub")
        try:
            parsed_user_id = UUID(user_id)
        except (TypeError, ValueError):
            raise UnauthorizedException("Invalid user")
        result = await self.db.execute(select(User).where(User.id == parsed_user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise UnauthorizedException("Invalid user")
        return self._tokens(user)

    @staticmethod
    def _tokens(user: User) -> TokenResponse:
        return TokenResponse(access_token=create_access_token(str(user.id)), refresh_token=create_refresh_token(str(user.id)))
