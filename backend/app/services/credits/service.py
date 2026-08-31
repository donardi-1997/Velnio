from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.credit import CreditWallet, CreditTransaction, TransactionType
from app.core.exceptions import InsufficientCreditsException, NotFoundException
from app.core.logging import get_logger

logger = get_logger(__name__)


class CreditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_wallet(self, workspace_id: UUID) -> CreditWallet:
        result = await self.db.execute(select(CreditWallet).where(CreditWallet.workspace_id == workspace_id))
        wallet = result.scalar_one_or_none()
        if not wallet:
            raise NotFoundException("Credit wallet")
        return wallet

    async def allocate(self, workspace_id: UUID, amount: float, description: str, reference_type: str = None, reference_id: UUID = None) -> CreditTransaction:
        wallet = await self.get_wallet(workspace_id)
        wallet.balance += amount
        wallet.lifetime_credits += amount
        tx = CreditTransaction(
            workspace_id=workspace_id,
            wallet_id=wallet.id,
            amount=amount,
            transaction_type=TransactionType.ALLOCATION,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def consume(self, workspace_id: UUID, amount: float, description: str, reference_type: str = None, reference_id: UUID = None) -> CreditTransaction:
        wallet = await self.get_wallet(workspace_id)
        if wallet.balance < amount:
            raise InsufficientCreditsException()
        wallet.balance -= amount
        tx = CreditTransaction(
            workspace_id=workspace_id,
            wallet_id=wallet.id,
            amount=-amount,
            transaction_type=TransactionType.USAGE,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def refund(self, workspace_id: UUID, amount: float, description: str, reference_type: str = None, reference_id: UUID = None) -> CreditTransaction:
        wallet = await self.get_wallet(workspace_id)
        wallet.balance += amount
        tx = CreditTransaction(
            workspace_id=workspace_id,
            wallet_id=wallet.id,
            amount=amount,
            transaction_type=TransactionType.REFUND,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def adjust(self, workspace_id: UUID, amount: float, description: str) -> CreditTransaction:
        wallet = await self.get_wallet(workspace_id)
        wallet.balance = max(0, wallet.balance + amount)
        tx = CreditTransaction(
            workspace_id=workspace_id,
            wallet_id=wallet.id,
            amount=amount,
            transaction_type=TransactionType.ADJUSTMENT,
            description=description,
        )
        self.db.add(tx)
        await self.db.flush()
        return tx
