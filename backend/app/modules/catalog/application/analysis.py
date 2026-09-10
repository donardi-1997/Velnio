from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BadGatewayException,
    BadRequestException,
    InsufficientCreditsException,
    NotFoundException,
)
from app.core.logging import get_logger
from app.models.analysis import ProductAnalysis
from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.product import Product, ProductStatus
from app.services.ai import get_ai_provider

logger = get_logger(__name__)


class ProductAnalysisService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def analyze(self, product_id: UUID, workspace_id: UUID) -> ProductAnalysis:
        result = await self.db.execute(
            select(Product).where(Product.id == product_id, Product.workspace_id == workspace_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundException("Product")

        result = await self.db.execute(
            select(CreditWallet).where(CreditWallet.workspace_id == workspace_id)
        )
        wallet = result.scalar_one_or_none()
        if not wallet or wallet.balance < settings.PLAN_ANALYSIS_COST:
            raise InsufficientCreditsException()

        product.status = ProductStatus.ANALYZING
        await self.db.flush()

        try:
            analysis_data = await get_ai_provider().analyze_product(product)

            result = await self.db.execute(
                select(ProductAnalysis).where(ProductAnalysis.product_id == product.id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                await self.db.delete(existing)
                await self.db.flush()

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
            self.db.add(analysis)

            wallet.balance -= settings.PLAN_ANALYSIS_COST
            self.db.add(
                CreditTransaction(
                    workspace_id=workspace_id,
                    wallet_id=wallet.id,
                    amount=-settings.PLAN_ANALYSIS_COST,
                    transaction_type=TransactionType.USAGE,
                    description="Product analysis",
                    reference_type="product_analysis",
                    reference_id=product.id,
                )
            )

            product.status = ProductStatus.ANALYZED
            await self.db.flush()
            await self.db.refresh(analysis)
            return analysis
        except (InsufficientCreditsException, BadGatewayException):
            raise
        except Exception as exc:
            logger.error("Analysis failed type=%s", type(exc).__name__)
            product.status = ProductStatus.FAILED
            await self.db.flush()
            raise BadRequestException("Analysis failed. Please try again.") from exc
