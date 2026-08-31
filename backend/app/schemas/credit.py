from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class CreditWalletResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    balance: float
    lifetime_credits: float

    class Config:
        from_attributes = True


class CreditTransactionResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    amount: float
    transaction_type: str
    description: str
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True
