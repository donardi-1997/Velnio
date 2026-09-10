from fastapi import APIRouter

from app.api.routes import google_drive

router = APIRouter()
router.include_router(google_drive.router, prefix="/google-drive", tags=["google-drive"])
