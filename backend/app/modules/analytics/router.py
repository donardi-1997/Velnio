from fastapi import APIRouter

from app.api.routes import dashboard, performance, tracking

router = APIRouter()
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
router.include_router(performance.router, prefix="/campaigns", tags=["performance"])
router.include_router(tracking.router, prefix="/tracking", tags=["tracking"])
