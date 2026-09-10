from fastapi import APIRouter

from app.modules.campaigns.api import angles, briefs, campaigns, landings, offers, publishing

router = APIRouter()
router.include_router(campaigns.router)
router.include_router(angles.router)
router.include_router(offers.router)
router.include_router(landings.router)
router.include_router(publishing.router)
router.include_router(briefs.router)
