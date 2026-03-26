"""Billing admin API schemas based on the billing admin OpenAPI document."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


class BillingAdminSchema(BaseModel):
    """Base schema with strict field validation."""

    model_config = ConfigDict(extra="forbid")


BillingProductFamily = Literal["simulate", "classification"]
BillingProductType = Literal["subscription", "credit_pack"]
BillingGrantMode = Literal["unlimited", "prepaid_quota"]
BillingCurrency = Literal["usd"]
BillingRecurringInterval = Literal["day", "week", "month", "year"]
BillingStripeSyncMode = Literal["create", "bind_existing"]


class BillingAdminErrorDetail(BillingAdminSchema):
    """Billing admin error payload."""

    code: str = Field(..., description="Billing admin error code")
    message: str = Field(..., description="Human-readable error message")
    field_errors: dict[str, str] | None = Field(
        default=None,
        description="Optional field-level validation errors",
    )


class BillingAdminErrorResponse(BillingAdminSchema):
    """Billing admin error response wrapper."""

    detail: BillingAdminErrorDetail


class BillingProductConfigUnlimited(BillingAdminSchema):
    """Config for unlimited grant mode."""

    feature_key: str = Field(..., min_length=1, max_length=128)
    grant_mode: Literal["unlimited"]
    credits: None = Field(default=None)


class BillingProductConfigPrepaidQuota(BillingAdminSchema):
    """Config for prepaid quota grant mode."""

    feature_key: str = Field(..., min_length=1, max_length=128)
    grant_mode: Literal["prepaid_quota"]
    credits: int = Field(..., gt=0)


BillingProductConfigEntry = Annotated[
    BillingProductConfigUnlimited | BillingProductConfigPrepaidQuota,
    Field(discriminator="grant_mode"),
]

def _normalize_config_json_array(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return value


BillingProductConfigJson = Annotated[
    list[BillingProductConfigEntry],
    BeforeValidator(_normalize_config_json_array),
    Field(min_length=1),
]


class BillingProduct(BillingAdminSchema):
    """BillingProduct response model."""

    product_code: str = Field(..., min_length=1, max_length=64)
    product_family: BillingProductFamily
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    product_type: BillingProductType
    stripe_product_id: str
    stripe_price_id: str
    active: bool
    sort_order: int
    config_json: BillingProductConfigJson
    created_at: str
    updated_at: str


class GrantPreview(BillingAdminSchema):
    """GrantPreview response model."""

    feature_key: str
    grant_mode: BillingGrantMode
    granted_quantity: int | None


class StripeCatalogInfo(BillingAdminSchema):
    """Stripe catalog information returned by detail endpoints."""

    stripe_product_id: str
    stripe_price_id: str
    currency: BillingCurrency
    unit_amount: int
    billing_scheme: str
    recurring_interval: BillingRecurringInterval | None = None
    recurring_interval_count: int | None = Field(default=None, ge=1)
    lookup_key: str | None = None
    active: bool


class BillingProductDetail(BillingProduct):
    """Detailed BillingProduct response model."""

    grant_preview: list[GrantPreview]
    stripe_catalog: StripeCatalogInfo


class BillingProductListResponse(BillingAdminSchema):
    """Paginated list response."""

    items: list[BillingProduct]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)


class BillingCreateStripePriceRecurring(BillingAdminSchema):
    """Recurring Stripe price payload for create operations."""

    currency: BillingCurrency
    unit_amount: int = Field(..., gt=0)
    billing_scheme: str | None = None
    type: Literal["recurring"]
    recurring_interval: BillingRecurringInterval
    recurring_interval_count: int = Field(..., ge=1)
    lookup_key: str | None = None


class BillingCreateStripePriceOneTime(BillingAdminSchema):
    """One-time Stripe price payload for create operations."""

    currency: BillingCurrency
    unit_amount: int = Field(..., gt=0)
    billing_scheme: str
    type: Literal["one_time"]
    lookup_key: str | None = None


BillingCreateStripePrice = Annotated[
    BillingCreateStripePriceRecurring | BillingCreateStripePriceOneTime,
    Field(discriminator="type"),
]


class BillingCreateStripeSyncCreate(BillingAdminSchema):
    """Create-and-sync Stripe payload."""

    mode: Literal["create"]
    # TODO: OpenAPI example includes product_name, but the document does not define its requirement level.
    product_name: str | None = None
    price: BillingCreateStripePrice


class BillingCreateStripeSyncBindExisting(BillingAdminSchema):
    """Bind-existing Stripe payload."""

    mode: Literal["bind_existing"]
    stripe_product_id: str
    stripe_price_id: str


BillingCreateStripeSync = Annotated[
    BillingCreateStripeSyncCreate | BillingCreateStripeSyncBindExisting,
    Field(discriminator="mode"),
]


class BillingCreateProductRequest(BillingAdminSchema):
    """Create product request payload."""

    product_code: str = Field(..., min_length=1, max_length=64)
    product_family: BillingProductFamily
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    product_type: BillingProductType
    active: bool
    sort_order: int
    config_json: BillingProductConfigJson
    stripe_sync: BillingCreateStripeSync


class BillingUpdateStripePriceChangeDisabled(BillingAdminSchema):
    """Stripe price change disabled payload."""

    enabled: Literal[False]


class BillingUpdateStripePriceChangeRecurring(BillingAdminSchema):
    """Recurring Stripe price change payload."""

    enabled: Literal[True]
    currency: BillingCurrency
    unit_amount: int = Field(..., gt=0)
    billing_scheme: str | None = None
    type: Literal["recurring"]
    recurring_interval: BillingRecurringInterval
    recurring_interval_count: int = Field(..., ge=1)


class BillingUpdateStripePriceChangeOneTime(BillingAdminSchema):
    """One-time Stripe price change payload."""

    enabled: Literal[True]
    currency: BillingCurrency
    unit_amount: int = Field(..., gt=0)
    billing_scheme: str
    type: Literal["one_time"]


BillingUpdateStripePriceChange = (
    BillingUpdateStripePriceChangeDisabled
    | BillingUpdateStripePriceChangeRecurring
    | BillingUpdateStripePriceChangeOneTime
)


class BillingUpdateStripeSync(BillingAdminSchema):
    """Stripe sync payload for PUT updates."""

    update_product: bool
    price_change: BillingUpdateStripePriceChange | None = None


class BillingUpdateProductRequest(BillingAdminSchema):
    """Full update request payload."""

    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    active: bool
    sort_order: int
    config_json: BillingProductConfigJson
    stripe_sync: BillingUpdateStripeSync


class BillingPatchProductRequest(BillingAdminSchema):
    """Partial update request payload."""

    active: bool


class BillingSyncStripeRequest(BillingAdminSchema):
    """Manual sync request payload."""

    sync_product: bool
    sync_price: bool


class BillingSyncStripeResponse(BillingAdminSchema):
    """Manual sync response payload."""

    ok: bool
    product_code: str
    stripe_product_id: str
    stripe_price_id: str
