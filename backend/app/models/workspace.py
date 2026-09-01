import uuid
from sqlalchemy import Column, String, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import UUIDMixin, TimestampMixin
import enum


class MemberRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Workspace(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"

    name = Column(String(255), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="workspaces")
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    stores = relationship("Store", back_populates="workspace", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="workspace", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="workspace", cascade="all, delete-orphan")
    wallet = relationship("CreditWallet", back_populates="workspace", uselist=False, cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="workspace", uselist=False, cascade="all, delete-orphan")
    google_drive_connections = relationship("GoogleDriveConnection", back_populates="workspace", cascade="all, delete-orphan")
    knowledge_sources = relationship("KnowledgeSource", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")


class WorkspaceMember(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "workspace_members"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(SAEnum(MemberRole, name="member_role", create_constraint=True), nullable=False, default=MemberRole.MEMBER)

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="memberships")
