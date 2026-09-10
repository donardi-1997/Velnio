from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace
from app.db.session import get_db
from app.models.workspace import Workspace
from app.modules.billing.application.credits import CreditService
from app.modules.billing.infrastructure.repository import BillingRepository
from app.schemas.credit import CreditTransactionResponse, CreditWalletResponse

router = APIRouter()


def get_credit_service(db: AsyncSession = Depends(get_db)) -> CreditService:
    return CreditService(BillingRepository(db))


@router.get("", response_model=CreditWalletResponse)
async def get_credits(
    workspace: Workspace = Depends(get_current_workspace),
    service: CreditService = Depends(get_credit_service),
):
    return await service.get_wallet(workspace.id)


@router.get("/transactions", response_model=List[CreditTransactionResponse])
async def list_transactions(
    workspace: Workspace = Depends(get_current_workspace),
    service: CreditService = Depends(get_credit_service),
):
    return await service.list_transactions(workspace.id)
