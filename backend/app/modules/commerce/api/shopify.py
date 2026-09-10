from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.commerce.application.publishing import ProductPublishingService

router = APIRouter()


def get_product_publishing_service(
    db: AsyncSession = Depends(get_db),
) -> ProductPublishingService:
    return ProductPublishingService(db)


@router.post("/{product_id}/publish", status_code=200)
async def publish_product(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    service: ProductPublishingService = Depends(get_product_publishing_service),
):
    return await service.publish(product_id, workspace.id)
