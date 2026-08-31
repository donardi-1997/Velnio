from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.product import Product, ProductStatus
from app.models.landing import LandingPage, LandingStatus
from app.models.credit import CreditWallet
from app.schemas.dashboard import DashboardSummary
from app.api.deps import get_current_workspace

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    products_result = await db.execute(
        select(func.count(Product.id)).where(Product.workspace_id == workspace.id)
    )
    total_products = products_result.scalar() or 0

    analyzed_result = await db.execute(
        select(func.count(Product.id)).where(
            Product.workspace_id == workspace.id,
            Product.status.in_([ProductStatus.ANALYZED, ProductStatus.READY, ProductStatus.PUBLISHED]),
        )
    )
    analyzed_products = analyzed_result.scalar() or 0

    landings_result = await db.execute(
        select(func.count(LandingPage.id))
        .join(Product)
        .where(Product.workspace_id == workspace.id)
    )
    total_landings = landings_result.scalar() or 0

    published_result = await db.execute(
        select(func.count(Product.id)).where(
            Product.workspace_id == workspace.id,
            Product.status == ProductStatus.PUBLISHED,
        )
    )
    published_products = published_result.scalar() or 0

    wallet_result = await db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace.id))
    wallet = wallet_result.scalar_one_or_none()
    credits_remaining = wallet.balance if wallet else 0

    return DashboardSummary(
        total_products=total_products,
        analyzed_products=analyzed_products,
        total_landings=total_landings,
        published_products=published_products,
        credits_remaining=credits_remaining,
    )
