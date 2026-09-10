from __future__ import annotations

from typing import Sequence
from uuid import UUID

from app.core.exceptions import NotFoundException
from app.models.credit import CreditTransaction, CreditWallet
from app.modules.billing.infrastructure.repository import BillingRepository


class CreditService:
    def __init__(self, repository: BillingRepository) -> None:
        self.repository = repository

    async def get_wallet(self, workspace_id: UUID) -> CreditWallet:
        wallet = await self.repository.get_wallet(workspace_id)
        if wallet is None:
            raise NotFoundException("Credit wallet")
        return wallet

    async def list_transactions(self, workspace_id: UUID) -> Sequence[CreditTransaction]:
        return await self.repository.list_transactions(workspace_id, limit=50)
