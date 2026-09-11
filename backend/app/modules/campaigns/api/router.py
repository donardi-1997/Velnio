from fastapi import APIRouter

from app.modules.campaigns.api import (
    angles,
    briefs,
    campaigns,
    demo,
    landings,
    meta_ads,
    offers,
    publishing,
    variants,
    visual_assets,
)

router = APIRouter()

# Apply the public /campaigns prefix at each include boundary. FastAPI validates
# empty collection paths ("") against the prefix passed to include_router, so
# relying on a parent router prefix is insufficient for campaigns.router.
for feature_router in (
    campaigns.router,
    angles.router,
    offers.router,
    landings.router,
    publishing.router,
    briefs.router,
    visual_assets.router,
    variants.router,
    demo.router,
    meta_ads.router,
):
    router.include_router(feature_router, prefix="/campaigns")
