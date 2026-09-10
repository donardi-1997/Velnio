from fastapi import APIRouter

from app.api.routes import angles, campaigns, demo, landings, publish, variants, visual_assets

router = APIRouter()
router.include_router(angles.router, prefix="/products", tags=["angles"])
router.include_router(landings.router, prefix="/products", tags=["landings"])
router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
router.include_router(visual_assets.router, prefix="/campaigns", tags=["visual-assets"])
router.include_router(publish.router, prefix="/campaigns", tags=["publish"])
router.include_router(variants.router, prefix="/campaigns", tags=["variants"])
router.include_router(demo.router, prefix="/campaigns", tags=["demo"])
