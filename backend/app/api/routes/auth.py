from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, TokenRefresh, UserResponse
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, MemberRole
from app.models.credit import CreditWallet, CreditTransaction, TransactionType
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.exceptions import AppException, BadRequestException, UnauthorizedException
from app.core.config import settings
from app.api.deps import get_current_user
from uuid import UUID
from datetime import datetime, timezone

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise BadRequestException("Email already registered")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
    )
    db.add(user)
    await db.flush()

    workspace = Workspace(name=f"{data.first_name}'s Workspace", owner_id=user.id)
    db.add(workspace)
    await db.flush()

    member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=MemberRole.OWNER)
    db.add(member)

    plan_result = await db.execute(select(Plan).where(Plan.code == "FREE"))
    plan = plan_result.scalar_one_or_none()
    if plan:
        sub = Subscription(
            workspace_id=workspace.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc),
            provider="MOCK",
        )
        db.add(sub)

    wallet = CreditWallet(workspace_id=workspace.id, balance=settings.FREE_CREDITS, lifetime_credits=settings.FREE_CREDITS)
    db.add(wallet)
    await db.flush()

    tx = CreditTransaction(
        workspace_id=workspace.id,
        wallet_id=wallet.id,
        amount=settings.FREE_CREDITS,
        transaction_type=TransactionType.ALLOCATION,
        description=f"Free credits on registration",
    )
    db.add(tx)

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise UnauthorizedException("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedException("Account is disabled")
    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedException("Invalid user")
    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user
