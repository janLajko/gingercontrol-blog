"""SQLAlchemy models for blog posts, categories, and billing products."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


class BlogPost(Base):
    """Persisted generated blog post."""

    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    keyword: Mapped[str] = mapped_column(String(200), index=True)
    slug: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    author_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    author_avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cover_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customization: Mapped[dict] = mapped_column(JSONType, default=dict)
    sources_used: Mapped[list] = mapped_column(JSONType, default=list)
    source_details: Mapped[list] = mapped_column(JSONType, default=list)
    seo_scores: Mapped[dict] = mapped_column(JSONType, default=dict)
    final_score: Mapped[float] = mapped_column(Float, default=0.0)
    model_used: Mapped[str | None] = mapped_column(String(120), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    type: Mapped[str] = mapped_column(String(32), default="article", index=True)
    status: Mapped[str] = mapped_column(String(32), default="failed")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Category(Base):
    """Persisted category values for article classification."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class BillingProductRecord(Base):
    """Persisted billing product configuration and Stripe bindings."""

    __tablename__ = "billing_product"
    __table_args__ = (
        CheckConstraint(
            "product_type in ('subscription', 'credit_pack')",
            name="ck_billing_product_type",
        ),
    )

    product_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_family: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_type: Mapped[str] = mapped_column(String(32))
    stripe_product_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    stripe_price_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    config_json: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class BillingFeaturePolicyRecord(Base):
    """Persisted billing feature policy definitions."""

    __tablename__ = "billing_feature_policy"
    __table_args__ = (
        CheckConstraint(
            "control_mode in ('free', 'grant_required', 'blocked')",
            name="ck_billing_feature_policy_control_mode",
        ),
    )

    feature_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    control_mode: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    config_json: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
