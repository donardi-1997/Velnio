from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.identity.application.auth import IdentityService
from app.schemas.auth import TokenRefresh, TokenResponse, UserLogin, UserRegister, UserResponse

router = APIRouter()


def get_identity_service(db: AsyncSession = Depends(get_db)) -> IdentityService:
    return IdentityService(db)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, service: IdentityService = Depends(get_identity_service)):
    return await service.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, service: IdentityService = Depends(get_identity_service)):
    return await service.login(data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: TokenRefresh, service: IdentityService = Depends(get_identity_service)):
    return await service.refresh(data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user
