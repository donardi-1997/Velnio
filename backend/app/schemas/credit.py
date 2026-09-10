from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class CreditWalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    balance: float
    lifetime_credits: float


class CreditTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    amount: float
    transaction_type: str
    description: str
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    created_at: datetime
