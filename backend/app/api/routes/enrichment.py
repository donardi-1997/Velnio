from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.product import Product
from app.models.enrichment import ProductEnrichment
from app.models.credit import CreditWallet, CreditTransaction, TransactionType
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException, InsufficientCreditsException, BadRequestException
from app.core.config import settings
from app.core.logging import get_logger
from app.services.enrichment import ProductEnrichmentService
from uuid import UUID

logger = get_logger(__name__)
router = APIRouter()


@router.post("/{product_id}/enrich")
async def enrich_product(
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
    if not wallet or wallet.balance < settings.PLAN_ENRICHMENT_COST:
        raise InsufficientCreditsException()

    existing_result = await db.execute(select(ProductEnrichment).where(ProductEnrichment.product_id == product_id))
    existing = existing_result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.flush()

    try:
        service = ProductEnrichmentService()
        enrichment_data = await service.enrich(product)

        enrichment = ProductEnrichment(
            product_id=product_id,
            features=enrichment_data.get("features", []),
            benefits=enrichment_data.get("benefits", []),
            use_cases=enrichment_data.get("use_cases", []),
            suggested_audiences=enrichment_data.get("suggested_audiences", []),
            short_description=enrichment_data.get("short_description"),
            enriched_description=enrichment_data.get("enriched_description"),
        )
        db.add(enrichment)

        wallet.balance -= settings.PLAN_ENRICHMENT_COST
        tx = CreditTransaction(
            workspace_id=workspace.id,
            wallet_id=wallet.id,
            amount=-settings.PLAN_ENRICHMENT_COST,
            transaction_type=TransactionType.USAGE,
            description="Enrich product",
            reference_type="product_enrichment",
            reference_id=product_id,
        )
        db.add(tx)

        await db.flush()
        await db.refresh(enrichment)
        return enrichment

    except InsufficientCreditsException:
        raise
    except Exception as e:
        logger.error(f"Enrichment failed: {e}")
        raise BadRequestException("Enrichment failed. Please try again.")


@router.get("/{product_id}/enrichment")
async def get_enrichment(
    product_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace.id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundException("Product")

    enrich_result = await db.execute(select(ProductEnrichment).where(ProductEnrichment.product_id == product_id))
    enrichment = enrich_result.scalar_one_or_none()
    if not enrichment:
        raise NotFoundException("Enrichment not found. Run enrichment first.")
    return enrichment
