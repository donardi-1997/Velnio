import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, Text, Enum as SAEnum, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin


class KnowledgeSourceType(str, enum.Enum):
    CUSTOMER_SERVICE = "CUSTOMER_SERVICE"
    REVIEWS = "REVIEWS"
    COMPETITOR = "COMPETITOR"
    MANUAL = "MANUAL"
    SUPPLIER = "SUPPLIER"


class KnowledgeContentType(str, enum.Enum):
    DOCUMENT = "DOCUMENT"
    TEXT = "TEXT"
    URL = "URL"
    MANUAL = "MANUAL"


class KnowledgeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    STALE = "STALE"


class KnowledgeSource(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_sources"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    source_type = Column(String(50), nullable=False)
    content_type = Column(String(50), nullable=False)
    title = Column(String(512), nullable=False)
    content_text = Column(Text, nullable=True)
    url = Column(String(1024), nullable=True)
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("product_source_documents.id", ondelete="SET NULL"), nullable=True)
    content_hash = Column(String(64), nullable=True)
    imported_at = Column(DateTime(timezone=True), nullable=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    is_primary = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=False, default="ACTIVE")
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    workspace = relationship("Workspace", back_populates="knowledge_sources")
    product = relationship("Product", back_populates="knowledge_sources")
    campaign = relationship("Campaign", back_populates="knowledge_sources")
    source_document = relationship("ProductSourceDocument")
    created_by = relationship("User")
