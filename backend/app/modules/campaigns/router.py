from fastapi import APIRouter

from app.modules.campaigns.api import product_scope
from app.modules.campaigns.api.router import router as campaign_api_router

router = APIRouter()
router.include_router(product_scope.router, prefix="/products", tags=["angles", "landings"])
router.include_router(campaign_api_router, prefix="/campaigns", tags=["campaigns"])
