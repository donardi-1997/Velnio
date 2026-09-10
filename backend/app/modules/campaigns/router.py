from fastapi import APIRouter

from app.api.routes import angles, demo, landings, variants, visual_assets
from app.modules.campaigns.api.router import router as campaign_api_router

router = APIRouter()
router.include_router(angles.router, prefix="/products", tags=["angles"])
router.include_router(landings.router, prefix="/products", tags=["landings"])
router.include_router(campaign_api_router, prefix="/campaigns", tags=["campaigns"])
router.include_router(visual_assets.router, prefix="/campaigns", tags=["visual-assets"])
router.include_router(variants.router, prefix="/campaigns", tags=["variants"])
router.include_router(demo.router, prefix="/campaigns", tags=["demo"])
