from fastapi import APIRouter

from app.api.routes import enrichment, product_import
from app.modules.catalog.api import analysis, products

router = APIRouter()
router.include_router(products.router, prefix="/products", tags=["products"])
router.include_router(analysis.router, prefix="/products", tags=["ai"])
router.include_router(product_import.router, prefix="/products", tags=["import"])
router.include_router(enrichment.router, prefix="/products", tags=["enrichment"])
