from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.catalog.application.analysis import ProductAnalysisService
from app.schemas.analysis import AnalysisResponse

router = APIRouter()


@router.post("/{product_id}/analyze", response_model=AnalysisResponse)
async def analyze_product(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    return await ProductAnalysisService(db).analyze(product_id, workspace.id)
