from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.catalog.application.enrichment import CatalogEnrichmentService

router = APIRouter()


def get_enrichment_service(db: AsyncSession = Depends(get_db)) -> CatalogEnrichmentService:
    return CatalogEnrichmentService(db)


@router.post("/{product_id}/enrich")
async def enrich_product(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: CatalogEnrichmentService = Depends(get_enrichment_service),
):
    return await service.enrich(product_id, workspace.id)


@router.get("/{product_id}/enrichment")
async def get_enrichment(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: CatalogEnrichmentService = Depends(get_enrichment_service),
):
    return await service.get(product_id, workspace.id)
