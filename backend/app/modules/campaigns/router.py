from fastapi import APIRouter

from app.api.routes import angles, landings
from app.modules.campaigns.api.router import router as campaign_api_router

router = APIRouter()
router.include_router(angles.router, prefix="/products", tags=["angles"])
router.include_router(landings.router, prefix="/products", tags=["landings"])
router.include_router(campaign_api_router, prefix="/campaigns", tags=["campaigns"])
