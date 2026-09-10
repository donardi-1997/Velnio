from fastapi import APIRouter

from app.api.routes import shopify, stores

router = APIRouter()
router.include_router(stores.router, prefix="/stores", tags=["stores"])
router.include_router(shopify.router, prefix="/products", tags=["shopify"])
