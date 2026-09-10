from fastapi import APIRouter

from app.modules.billing.api import credits, subscriptions

router = APIRouter()
router.include_router(credits.router, prefix="/credits", tags=["credits"])
router.include_router(subscriptions.router, prefix="/billing", tags=["billing"])
