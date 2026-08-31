from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.credit import CreditWallet, CreditTransaction
from app.schemas.credit import CreditWalletResponse, CreditTransactionResponse
from app.api.deps import get_current_workspace
from app.core.exceptions import NotFoundException
from typing import List

router = APIRouter()


@router.get("", response_model=CreditWalletResponse)
async def get_credits(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace.id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise NotFoundException("Credit wallet")
    return wallet


@router.get("/transactions", response_model=List[CreditTransactionResponse])
async def list_transactions(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.workspace_id == workspace.id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()
