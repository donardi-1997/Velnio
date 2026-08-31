import uuid
from sqlalchemy import Column, String, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin
import enum


class StorePlatform(str, enum.Enum):
    SHOPIFY = "SHOPIFY"


class StoreStatus(str, enum.Enum):
    DISCONNECTED = "DISCONNECTED"
    PENDING = "PENDING"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"


class Store(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "stores"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(255), nullable=False)
    shop_domain = Column(String(512), nullable=True)
    platform = Column(SAEnum(StorePlatform, name="store_platform", create_constraint=True), nullable=False, default=StorePlatform.SHOPIFY)
    access_token_encrypted = Column(String(1024), nullable=True)
    status = Column(SAEnum(StoreStatus, name="store_status", create_constraint=True), nullable=False, default=StoreStatus.DISCONNECTED)
    country = Column(String(2), nullable=False, default="US")
    currency = Column(String(3), nullable=False, default="USD")

    workspace = relationship("Workspace", back_populates="stores")
    products = relationship("Product", back_populates="store")
    campaigns = relationship("Campaign", back_populates="store")
