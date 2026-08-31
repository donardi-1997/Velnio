import uuid
from sqlalchemy import Column, String, ForeignKey, Text, Enum as SAEnum, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin
import enum


class DocumentImportStatus(str, enum.Enum):
    IMPORTED = "IMPORTED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class GoogleDriveConnection(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "google_drive_connections"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=False)
    token_expiry = Column(DateTime(timezone=True), nullable=True)
    scope = Column(String(512), nullable=False)
    google_email = Column(String(255), nullable=True)
    google_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    workspace = relationship("Workspace", back_populates="google_drive_connections")


class ProductSourceDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "product_source_documents"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    external_file_id = Column(String(255), nullable=False)
    external_file_name = Column(String(512), nullable=True)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="IMPORTED")
    storage_key = Column(String(512), nullable=True)
    content_text = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    imported_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    product = relationship("Product", back_populates="source_documents")
    campaign = relationship("Campaign", back_populates="source_documents")
