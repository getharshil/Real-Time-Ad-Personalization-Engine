"""
SQLAlchemy ORM models for the AI Personalization Platform.

Demonstrates:
- Proper relational modeling with foreign keys
- CHECK constraints for data integrity
- UNIQUE constraints to prevent duplicates
- Indexes on frequently queried columns
- Timestamps for audit trails
- Relationships for ORM navigation
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.database import Base


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    device_type = Column(String(20), default="desktop")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_active_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    sessions = relationship("UserSession", back_populates="user", lazy="selectin")
    interests = relationship("UserInterest", back_populates="user", lazy="selectin")
    events = relationship("Event", back_populates="user", lazy="noload")
    recommendations = relationship("Recommendation", back_populates="user", lazy="noload")
    ab_assignments = relationship("ABTestAssignment", back_populates="user", lazy="noload")


# ---------------------------------------------------------------------------
# User Sessions
# ---------------------------------------------------------------------------

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    device_type = Column(String(20), default="desktop")

    # Relationships
    user = relationship("User", back_populates="sessions")
    events = relationship("Event", back_populates="session", lazy="noload")

    __table_args__ = (
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_started", "started_at"),
        CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="chk_session_duration"),
    )


# ---------------------------------------------------------------------------
# Content Categories
# ---------------------------------------------------------------------------

class ContentCategory(Base):
    __tablename__ = "content_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Relationships
    content_items = relationship("Content", back_populates="category", lazy="noload")
    advertisements = relationship("Advertisement", back_populates="target_category", lazy="noload")
    user_interests = relationship("UserInterest", back_populates="category", lazy="noload")


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

class Content(Base):
    __tablename__ = "content"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("content_categories.id", ondelete="SET NULL"), nullable=True)
    popularity_score = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    category = relationship("ContentCategory", back_populates="content_items", lazy="joined")

    __table_args__ = (
        Index("idx_content_category", "category_id"),
        Index("idx_content_active", "is_active"),
        CheckConstraint("popularity_score >= 0.0 AND popularity_score <= 1.0", name="chk_content_popularity"),
    )


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

VALID_EVENT_TYPES = (
    "APP_OPEN", "SEARCH", "CONTENT_VIEW", "CONTENT_LIKE", "CONTENT_DISLIKE",
    "AD_IMPRESSION", "AD_CLICK", "AD_SKIP", "SESSION_START", "SESSION_END",
)

class Event(Base):
    __tablename__ = "events"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("user_sessions.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(30), nullable=False)
    entity_type = Column(String(30), nullable=True)  # 'content', 'advertisement'
    entity_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True)

    # Relationships
    user = relationship("User", back_populates="events")
    session = relationship("UserSession", back_populates="events")

    __table_args__ = (
        Index("idx_events_user_id", "user_id"),
        Index("idx_events_type", "event_type"),
        Index("idx_events_created", "created_at"),
        Index("idx_events_user_type", "user_id", "event_type"),
        Index("idx_events_entity", "entity_type", "entity_id"),
        CheckConstraint(
            f"event_type IN ({', '.join(repr(t) for t in VALID_EVENT_TYPES)})",
            name="chk_event_type",
        ),
    )


# ---------------------------------------------------------------------------
# User Interests (dynamic profile)
# ---------------------------------------------------------------------------

class UserInterest(Base):
    __tablename__ = "user_interests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("content_categories.id", ondelete="CASCADE"), nullable=False)
    affinity_score = Column(Float, default=0.0, nullable=False)
    interaction_count = Column(Integer, default=0, nullable=False)
    last_interaction_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="interests")
    category = relationship("ContentCategory", back_populates="user_interests", lazy="joined")

    __table_args__ = (
        UniqueConstraint("user_id", "category_id", name="uq_user_category"),
        Index("idx_user_interests_user", "user_id"),
        CheckConstraint("affinity_score >= 0.0 AND affinity_score <= 1.0", name="chk_affinity_score"),
        CheckConstraint("interaction_count >= 0", name="chk_interaction_count"),
    )


# ---------------------------------------------------------------------------
# Advertisers
# ---------------------------------------------------------------------------

class Advertiser(Base):
    __tablename__ = "advertisers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    contact_email = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    campaigns = relationship("Campaign", back_populates="advertiser", lazy="selectin")


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("advertisers.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    budget = Column(Float, nullable=False)
    spent = Column(Float, default=0.0, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    advertiser = relationship("Advertiser", back_populates="campaigns")
    advertisements = relationship("Advertisement", back_populates="campaign", lazy="selectin")

    __table_args__ = (
        Index("idx_campaigns_advertiser", "advertiser_id"),
        Index("idx_campaigns_active", "is_active"),
        CheckConstraint("budget > 0", name="chk_campaign_budget"),
        CheckConstraint("spent >= 0", name="chk_campaign_spent"),
        CheckConstraint("end_date >= start_date", name="chk_campaign_dates"),
    )


# ---------------------------------------------------------------------------
# Advertisements
# ---------------------------------------------------------------------------

class Advertisement(Base):
    __tablename__ = "advertisements"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    target_category_id = Column(Integer, ForeignKey("content_categories.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    cta_text = Column(String(100), default="Learn More")
    landing_url = Column(String(500), nullable=True)
    bid_amount = Column(Float, nullable=False)
    frequency_cap = Column(Integer, default=10)  # max impressions per user
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="advertisements")
    target_category = relationship("ContentCategory", back_populates="advertisements", lazy="joined")
    impressions = relationship("AdImpression", back_populates="advertisement", lazy="noload")
    clicks = relationship("AdClick", back_populates="advertisement", lazy="noload")

    __table_args__ = (
        Index("idx_ads_campaign", "campaign_id"),
        Index("idx_ads_category", "target_category_id"),
        Index("idx_ads_active", "is_active"),
        CheckConstraint("bid_amount > 0", name="chk_bid_amount"),
        CheckConstraint("frequency_cap > 0", name="chk_frequency_cap"),
    )


# ---------------------------------------------------------------------------
# Ad Impressions
# ---------------------------------------------------------------------------

class AdImpression(Base):
    __tablename__ = "ad_impressions"

    id = Column(BigInteger, primary_key=True, index=True)
    ad_id = Column(Integer, ForeignKey("advertisements.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("user_sessions.id", ondelete="SET NULL"), nullable=True)
    recommendation_score = Column(Float, nullable=True)
    source = Column(String(50), default="recommendation")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    advertisement = relationship("Advertisement", back_populates="impressions")
    user = relationship("User")
    clicks = relationship("AdClick", back_populates="impression", lazy="noload")

    __table_args__ = (
        Index("idx_impressions_ad", "ad_id"),
        Index("idx_impressions_user", "user_id"),
        Index("idx_impressions_created", "created_at"),
    )


# ---------------------------------------------------------------------------
# Ad Clicks
# ---------------------------------------------------------------------------

class AdClick(Base):
    __tablename__ = "ad_clicks"

    id = Column(BigInteger, primary_key=True, index=True)
    impression_id = Column(BigInteger, ForeignKey("ad_impressions.id", ondelete="SET NULL"), nullable=True)
    ad_id = Column(Integer, ForeignKey("advertisements.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    impression = relationship("AdImpression", back_populates="clicks")
    advertisement = relationship("Advertisement", back_populates="clicks")
    user = relationship("User")

    __table_args__ = (
        Index("idx_clicks_ad", "ad_id"),
        Index("idx_clicks_user", "user_id"),
        Index("idx_clicks_created", "created_at"),
    )


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ad_id = Column(Integer, ForeignKey("advertisements.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=False)
    algorithm = Column(String(50), nullable=False)  # 'popularity', 'personalized', 'ml_ctr'
    was_shown = Column(Boolean, default=False)
    was_clicked = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="recommendations")
    advertisement = relationship("Advertisement")

    __table_args__ = (
        Index("idx_recommendations_user", "user_id", "created_at"),
        Index("idx_recommendations_algorithm", "algorithm"),
    )


# ---------------------------------------------------------------------------
# A/B Testing
# ---------------------------------------------------------------------------

class ABExperiment(Base):
    __tablename__ = "ab_experiments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    variant_a_name = Column(String(100), nullable=False, default="control")
    variant_b_name = Column(String(100), nullable=False, default="treatment")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    assignments = relationship("ABTestAssignment", back_populates="experiment", lazy="noload")


class ABTestAssignment(Base):
    __tablename__ = "ab_test_assignments"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("ab_experiments.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    variant = Column(String(10), nullable=False)  # 'A' or 'B'
    assigned_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    experiment = relationship("ABExperiment", back_populates="assignments")
    user = relationship("User", back_populates="ab_assignments")

    __table_args__ = (
        UniqueConstraint("experiment_id", "user_id", name="uq_experiment_user"),
        Index("idx_ab_experiment", "experiment_id"),
        Index("idx_ab_user", "user_id"),
        CheckConstraint("variant IN ('A', 'B')", name="chk_variant"),
    )
