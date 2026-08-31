from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.product import Product, ProductStatus
from app.models.analysis import ProductAnalysis
from app.models.credit import CreditWallet, CreditTransaction, TransactionType
from app.schemas.analysis import AnalysisResponse
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException, InsufficientCreditsException, BadRequestException
from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai import get_ai_provider
from uuid import UUID
from datetime import datetime, timezone

logger = get_logger(__name__)
router = APIRouter()


@router.post("/{product_id}/analyze", response_model=AnalysisResponse)
async def analyze_product(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundException("Product")

    wallet_result = await db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace.id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet or wallet.balance < settings.PLAN_ANALYSIS_COST:
        raise InsufficientCreditsException()

    product.status = ProductStatus.ANALYZING
    await db.flush()

    try:
        ai = get_ai_provider()
        analysis_data = await ai.analyze_product(product)

        existing = await db.execute(select(ProductAnalysis).where(ProductAnalysis.product_id == product.id))
        existing_analysis = existing.scalar_one_or_none()
        if existing_analysis:
            await db.delete(existing_analysis)
            await db.flush()

        analysis = ProductAnalysis(
            product_id=product.id,
            overall_score=analysis_data["overall_score"],
            demand_score=analysis_data["demand_score"],
            visual_score=analysis_data["visual_score"],
            problem_score=analysis_data["problem_score"],
            margin_score=analysis_data["margin_score"],
            saturation_score=analysis_data["saturation_score"],
            ad_potential_score=analysis_data["ad_potential_score"],
            impulse_score=analysis_data["impulse_score"],
            return_risk_score=analysis_data["return_risk_score"],
            summary=analysis_data["summary"],
            strengths=analysis_data["strengths"],
            risks=analysis_data["risks"],
            recommended_price_min=analysis_data.get("recommended_price_min"),
            recommended_price_max=analysis_data.get("recommended_price_max"),
            generated_at=datetime.now(timezone.utc),
        )
        db.add(analysis)

        wallet.balance -= settings.PLAN_ANALYSIS_COST
        tx = CreditTransaction(
            workspace_id=workspace.id,
            wallet_id=wallet.id,
            amount=-settings.PLAN_ANALYSIS_COST,
            transaction_type=TransactionType.USAGE,
            description="Product analysis",
            reference_type="product_analysis",
            reference_id=product.id,
        )
        db.add(tx)

        product.status = ProductStatus.ANALYZED
        await db.flush()
        await db.refresh(analysis)
        return analysis

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        product.status = ProductStatus.FAILED
        await db.flush()
        raise BadRequestException("Analysis failed. Please try again.")
