import uuid
from sqlalchemy import Column, String, ForeignKey, Float, Enum as SAEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin
import enum


class TransactionType(str, enum.Enum):
    ALLOCATION = "ALLOCATION"
    USAGE = "USAGE"
    PURCHASE = "PURCHASE"
    REFUND = "REFUND"
    ADJUSTMENT = "ADJUSTMENT"


class CreditWallet(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "credit_wallets"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, unique=True)
    balance = Column(Float, nullable=False, default=0)
    lifetime_credits = Column(Float, nullable=False, default=0)

    workspace = relationship("Workspace", back_populates="wallet")
    transactions = relationship("CreditTransaction", back_populates="wallet", cascade="all, delete-orphan", order_by="CreditTransaction.created_at.desc()")


class CreditTransaction(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "credit_transactions"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("credit_wallets.id"), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(SAEnum(TransactionType, name="transaction_type", create_constraint=True), nullable=False)
    description = Column(Text, nullable=False, default="")
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)

    wallet = relationship("CreditWallet", back_populates="transactions")
