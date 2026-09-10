from fastapi import APIRouter

from app.api.routes import billing, credits

router = APIRouter()
router.include_router(credits.router, prefix="/credits", tags=["credits"])
router.include_router(billing.router, prefix="/billing", tags=["billing"])
