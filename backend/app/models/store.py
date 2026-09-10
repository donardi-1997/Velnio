import enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


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
    platform = Column(
        SAEnum(StorePlatform, name="store_platform", create_constraint=True),
        nullable=False,
        default=StorePlatform.SHOPIFY,
    )
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    refresh_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    granted_scopes = Column(String(1024), nullable=True)
    status = Column(
        SAEnum(StoreStatus, name="store_status", create_constraint=True),
        nullable=False,
        default=StoreStatus.DISCONNECTED,
    )
    country = Column(String(2), nullable=False, default="US")
    currency = Column(String(3), nullable=False, default="USD")

    workspace = relationship("Workspace", back_populates="stores")
    products = relationship("Product", back_populates="store")
    campaigns = relationship("Campaign", back_populates="store")


class ShopifyOAuthState(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "shopify_oauth_states"

    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shop_domain = Column(String(255), nullable=False, index=True)
    nonce_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
