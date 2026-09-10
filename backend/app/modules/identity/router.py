from fastapi import APIRouter

from app.api.routes import auth, workspace

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
