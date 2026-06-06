"""SQLAlchemy models for blog posts, categories, users, and billing entities."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
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


class UserRecord(Base):
    """Persisted user accounts."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_name: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class BillingPurchaseRecord(Base):
    """Persisted purchase rows for Stripe and admin-manual grants."""

    __tablename__ = "billing_purchase"
    __table_args__ = (
        CheckConstraint(
            "purchase_type in ('subscription', 'one_time')",
            name="ck_billing_purchase_type",
        ),
        CheckConstraint(
            "status in ('pending', 'active', 'expired', 'canceled', 'consumed', 'failed')",
            name="ck_billing_purchase_status",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subject_type: Mapped[str] = mapped_column(String(32), index=True)
    subject_id: Mapped[int] = mapped_column(BigInteger, index=True)
    product_code: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("billing_product.product_code"),
        index=True,
    )
    purchase_type: Mapped[str] = mapped_column(String(32))
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    stripe_price_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONType, default=dict)
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


class BillingEntitlementGrantRecord(Base):
    """Persisted entitlement grants bound to purchases."""

    __tablename__ = "billing_entitlement_grant"
    __table_args__ = (
        CheckConstraint(
            "grant_mode in ('unlimited', 'prepaid_quota', 'blocked')",
            name="ck_billing_entitlement_grant_mode",
        ),
        CheckConstraint(
            "status in ('active', 'expired', 'consumed', 'canceled')",
            name="ck_billing_entitlement_grant_status",
        ),
        CheckConstraint(
            "granted_quantity is null or granted_quantity >= 0",
            name="ck_billing_entitlement_grant_quantity_nonnegative",
        ),
        CheckConstraint(
            "remaining_quantity is null or remaining_quantity >= 0",
            name="ck_billing_entitlement_grant_remaining_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    purchase_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("billing_purchase.id"),
        index=True,
    )
    subject_type: Mapped[str] = mapped_column(String(32), index=True)
    subject_id: Mapped[int] = mapped_column(BigInteger, index=True)
    feature_key: Mapped[str] = mapped_column(String(128), index=True)
    grant_mode: Mapped[str] = mapped_column(String(32))
    granted_quantity: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    remaining_quantity: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    config_json: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class BillingUsageEventRecord(Base):
    """Persisted usage rows for balance and audit views."""

    __tablename__ = "billing_usage_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    subject_type: Mapped[str] = mapped_column(String(32), index=True)
    subject_id: Mapped[int] = mapped_column(BigInteger, index=True)
    feature_key: Mapped[str] = mapped_column(String(128), index=True)
    grant_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("billing_entitlement_grant.id"),
        nullable=True,
        index=True,
    )
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(BigInteger, default=1)
    usage_status: Mapped[str] = mapped_column(String(32), index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    committed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    discarded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OpenApiClientRecord(Base):
    """Persisted OpenAPI client records."""

    __tablename__ = "t_openapi_client"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'disabled')",
            name="chk_t_openapi_client_status",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    client_code: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class OpenApiKeyRecord(Base):
    """Persisted OpenAPI key metadata and encrypted key copy."""

    __tablename__ = "t_openapi_key"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'revoked')",
            name="chk_t_openapi_key_status",
        ),
        CheckConstraint("rpm_limit > 0", name="chk_t_openapi_key_rpm_limit"),
        CheckConstraint("burst_limit > 0", name="chk_t_openapi_key_burst_limit"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    client_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("t_openapi_client.id"),
        index=True,
    )
    key_prefix: Mapped[str] = mapped_column(String(64))
    key_hash: Mapped[str] = mapped_column(String(128), unique=True)
    encrypted_key_ciphertext: Mapped[str] = mapped_column(Text)
    encrypted_key_nonce: Mapped[str] = mapped_column(String(128))
    encrypted_key_algorithm: Mapped[str] = mapped_column(String(32))
    secret_version: Mapped[str] = mapped_column(String(32), default="v1")
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rpm_limit: Mapped[int] = mapped_column(Integer, default=600)
    burst_limit: Mapped[int] = mapped_column(Integer, default=150)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
