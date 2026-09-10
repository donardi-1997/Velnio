from fastapi import APIRouter

from app.modules.catalog.api import analysis, enrichment, imports, products

router = APIRouter()
router.include_router(products.router, prefix="/products", tags=["products"])
router.include_router(analysis.router, prefix="/products", tags=["ai"])
router.include_router(imports.router, prefix="/products", tags=["import"])
router.include_router(enrichment.router, prefix="/products", tags=["enrichment"])
