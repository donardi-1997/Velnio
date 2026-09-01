import uuid
from sqlalchemy import Column, String, ForeignKey, Text, Enum as SAEnum, Float, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin
import enum


class SourceType(str, enum.Enum):
    MANUAL = "MANUAL"
    ALIEXPRESS = "ALIEXPRESS"
    AMAZON = "AMAZON"
    CJ = "CJ"
    OTHER = "OTHER"


class ProductStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    READY = "READY"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class ImageSourceType(str, enum.Enum):
    SOURCE = "SOURCE"
    UPLOADED = "UPLOADED"
    AI_GENERATED = "AI_GENERATED"


class ImagePurpose(str, enum.Enum):
    ORIGINAL = "ORIGINAL"
    HERO = "HERO"
    LIFESTYLE = "LIFESTYLE"
    PROBLEM = "PROBLEM"
    SOLUTION = "SOLUTION"
    BENEFIT = "BENEFIT"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    COMPARISON = "COMPARISON"
    SOCIAL = "SOCIAL"
    OTHER = "OTHER"


class Product(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "products"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=True)
    name = Column(String(512), nullable=False)
    source_type = Column(SAEnum(SourceType, name="source_type", create_constraint=True), nullable=False, default=SourceType.MANUAL)
    source_url = Column(String(1024), nullable=True)
    supplier_price = Column(Float, nullable=True)
    selling_price = Column(Float, nullable=True)
    currency = Column(String(3), nullable=False, default="USD")
    description = Column(Text, nullable=True)
    target_country = Column(String(2), nullable=False, default="US")
    target_language = Column(String(10), nullable=False, default="en")
    status = Column(SAEnum(ProductStatus, name="product_status", create_constraint=True), nullable=False, default=ProductStatus.DRAFT)
    published_product_id = Column(String(255), nullable=True)

    source_domain = Column(String(512), nullable=True)
    source_external_id = Column(String(255), nullable=True)
    source_metadata = Column(JSON, nullable=True)

    workspace = relationship("Workspace", back_populates="products")
    store = relationship("Store", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.position", lazy="selectin")
    analysis = relationship("ProductAnalysis", back_populates="product", uselist=False, cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="product", cascade="all, delete-orphan")
    enrichment = relationship("ProductEnrichment", back_populates="product", uselist=False, cascade="all, delete-orphan")
    source_documents = relationship("ProductSourceDocument", back_populates="product", cascade="all, delete-orphan", lazy="selectin")
    knowledge_sources = relationship("KnowledgeSource", back_populates="product", cascade="all, delete-orphan", lazy="selectin")


class ProductImage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "product_images"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String(1024), nullable=False)
    image_type = Column(String(50), nullable=False, default="main")
    position = Column(Integer, nullable=False, default=0)
    generated_by_ai = Column(String(50), nullable=False, default="false")

    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    source_type = Column(String(50), nullable=False, default="SOURCE")
    purpose = Column(String(50), nullable=False, default="ORIGINAL")
    storage_key = Column(String(512), nullable=True)
    prompt = Column(Text, nullable=True)
    generation_provider = Column(String(50), nullable=True)
    generation_model = Column(String(100), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    selected = Column(Boolean, nullable=False, default=False)

    external_source = Column(String(50), nullable=True)
    external_file_id = Column(String(255), nullable=True)
    external_file_name = Column(String(512), nullable=True)

    product = relationship("Product", back_populates="images")
    campaign = relationship("Campaign", back_populates="images")
