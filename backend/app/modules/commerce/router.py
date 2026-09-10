from fastapi import APIRouter

from app.modules.commerce.api import shopify, stores

router = APIRouter()
router.include_router(stores.router, prefix="/stores", tags=["stores"])
router.include_router(shopify.router, prefix="/products", tags=["shopify"])
