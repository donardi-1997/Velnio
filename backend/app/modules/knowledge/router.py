from fastapi import APIRouter

from app.api.routes import knowledge

router = APIRouter()
router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
