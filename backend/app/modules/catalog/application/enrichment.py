from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, InsufficientCreditsException, NotFoundException
from app.core.logging import get_logger
from app.models.credit import CreditTransaction, CreditWallet, TransactionType
from app.models.enrichment import ProductEnrichment
from app.models.product import Product
from app.services.enrichment import ProductEnrichmentService

logger = get_logger(__name__)


class CatalogEnrichmentService:
    """Application service for product enrichment use cases."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_product(self, product_id: UUID, workspace_id: UUID) -> Product:
        result = await self.db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.workspace_id == workspace_id,
            )
        )
        product = result.scalar_one_or_none()
        if product is None:
            raise NotFoundException("Product")
        return product

    async def get(self, product_id: UUID, workspace_id: UUID) -> ProductEnrichment:
        await self._get_product(product_id, workspace_id)
        result = await self.db.execute(
            select(ProductEnrichment).where(ProductEnrichment.product_id == product_id)
        )
        enrichment = result.scalar_one_or_none()
        if enrichment is None:
            raise NotFoundException("Enrichment not found. Run enrichment first.")
        return enrichment

    async def enrich(self, product_id: UUID, workspace_id: UUID) -> ProductEnrichment:
        product = await self._get_product(product_id, workspace_id)

        wallet_result = await self.db.execute(
            select(CreditWallet).where(CreditWallet.workspace_id == workspace_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        if wallet is None or wallet.balance < settings.PLAN_ENRICHMENT_COST:
            raise InsufficientCreditsException()

        existing_result = await self.db.execute(
            select(ProductEnrichment).where(ProductEnrichment.product_id == product_id)
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            await self.db.delete(existing)
            await self.db.flush()

        try:
            enrichment_data = await ProductEnrichmentService().enrich(product)
            enrichment = ProductEnrichment(
                product_id=product_id,
                features=enrichment_data.get("features", []),
                benefits=enrichment_data.get("benefits", []),
                use_cases=enrichment_data.get("use_cases", []),
                suggested_audiences=enrichment_data.get("suggested_audiences", []),
                short_description=enrichment_data.get("short_description"),
                enriched_description=enrichment_data.get("enriched_description"),
            )
            self.db.add(enrichment)

            wallet.balance -= settings.PLAN_ENRICHMENT_COST
            self.db.add(
                CreditTransaction(
                    workspace_id=workspace_id,
                    wallet_id=wallet.id,
                    amount=-settings.PLAN_ENRICHMENT_COST,
                    transaction_type=TransactionType.USAGE,
                    description="Enrich product",
                    reference_type="product_enrichment",
                    reference_id=product_id,
                )
            )

            await self.db.flush()
            await self.db.refresh(enrichment)
            return enrichment
        except InsufficientCreditsException:
            raise
        except Exception as exc:
            logger.error(f"Enrichment failed: {exc}")
            raise BadRequestException("Enrichment failed. Please try again.")
