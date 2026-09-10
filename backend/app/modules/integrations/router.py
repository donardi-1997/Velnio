from fastapi import APIRouter

from app.modules.integrations.api import google_drive, meta_ads

router = APIRouter()
router.include_router(google_drive.router, prefix="/google-drive", tags=["google-drive"])
router.include_router(meta_ads.router, prefix="/meta-ads", tags=["meta-ads"])
