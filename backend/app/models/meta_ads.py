from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Text, UniqueConstraint
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


class MetaAdsCampaignPublication(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "meta_ads_campaign_publications"

    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ad_account_id = Column(String(64), nullable=False, index=True)
    remote_campaign_id = Column(String(128), nullable=False, unique=True)
    remote_campaign_name = Column(String(512), nullable=False)
    objective = Column(String(64), nullable=False, default="OUTCOME_SALES")
    remote_status = Column(String(32), nullable=False, default="PAUSED")
    pixel_id = Column(String(128), nullable=True)
    page_id = Column(String(128), nullable=True)
    instagram_account_id = Column(String(128), nullable=True)
    delivery_configured_at = Column(DateTime(timezone=True), nullable=True)
    delivery_configured_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "ad_account_id",
            name="uq_meta_ads_campaign_publication_campaign_account",
        ),
    )


class MetaAdsAdSetPublication(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "meta_ads_ad_set_publications"

    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_publication_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meta_ads_campaign_publications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    remote_ad_set_id = Column(String(128), nullable=False, unique=True)
    remote_ad_set_name = Column(String(512), nullable=False)
    remote_status = Column(String(32), nullable=False, default="PAUSED")
    target_country = Column(String(2), nullable=False)
    daily_budget_minor = Column(BigInteger, nullable=False)
    currency = Column(String(3), nullable=False)
    optimization_goal = Column(String(64), nullable=False, default="OFFSITE_CONVERSIONS")
    billing_event = Column(String(64), nullable=False, default="IMPRESSIONS")
    bid_strategy = Column(String(64), nullable=False, default="LOWEST_COST_WITHOUT_CAP")


class MetaAdsCreativePublication(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "meta_ads_creative_publications"

    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_publication_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meta_ads_campaign_publications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ad_set_publication_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meta_ads_ad_set_publications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("product_images.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    idempotency_key = Column(String(64), nullable=False, unique=True, index=True)
    remote_creative_id = Column(String(128), nullable=False, unique=True)
    remote_creative_name = Column(String(512), nullable=False)
    destination_url = Column(String(2048), nullable=False)
    image_url = Column(String(2048), nullable=False)
    primary_text = Column(Text, nullable=False)
    headline = Column(String(255), nullable=True)
    call_to_action = Column(String(64), nullable=False, default="SHOP_NOW")
    page_id = Column(String(128), nullable=False)
    instagram_account_id = Column(String(128), nullable=True)


class MetaAdsAdPublication(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "meta_ads_ad_publications"

    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_publication_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meta_ads_campaign_publications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ad_set_publication_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meta_ads_ad_set_publications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creative_publication_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meta_ads_creative_publications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    idempotency_key = Column(String(64), nullable=False, unique=True, index=True)
    remote_ad_id = Column(String(128), nullable=False, unique=True)
    remote_ad_name = Column(String(512), nullable=False)
    remote_status = Column(String(32), nullable=False, default="PAUSED")

    __table_args__ = (
        UniqueConstraint(
            "ad_set_publication_id",
            "creative_publication_id",
            name="uq_meta_ads_ad_publication_adset_creative",
        ),
    )
