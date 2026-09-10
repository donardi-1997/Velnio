from fastapi import APIRouter

from app.modules.integrations.api import google_drive

router = APIRouter()
router.include_router(google_drive.router, prefix="/google-drive", tags=["google-drive"])
