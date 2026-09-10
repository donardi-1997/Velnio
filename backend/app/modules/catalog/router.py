from fastapi import APIRouter

from app.api.routes import ai, enrichment, product_import, products

router = APIRouter()
router.include_router(products.router, prefix="/products", tags=["products"])
router.include_router(ai.router, prefix="/products", tags=["ai"])
router.include_router(product_import.router, prefix="/products", tags=["import"])
router.include_router(enrichment.router, prefix="/products", tags=["enrichment"])
