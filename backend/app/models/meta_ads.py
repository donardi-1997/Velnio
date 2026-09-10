from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class MetaAdsConnection(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "meta_ads_connections"

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
    access_token_encrypted = Column(Text, nullable=False)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(String(1024), nullable=False)
    meta_user_id = Column(String(255), nullable=False)
    meta_user_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)


class MetaAdsOAuthState(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "meta_ads_oauth_states"

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
    nonce_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
