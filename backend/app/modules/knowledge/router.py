from fastapi import APIRouter

from app.modules.knowledge.api import sources

router = APIRouter()
router.include_router(sources.router, prefix="/knowledge", tags=["knowledge"])
