"""Billing admin API schemas based on the billing admin OpenAPI document."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    model_validator,
)


class BillingAdminSchema(BaseModel):
    """Base schema with strict field validation."""

    model_config = ConfigDict(extra="forbid")


BillingProductFamily = Literal["simulate", "classification", "system", "credits"]
BillingProductType = Literal["subscription", "credit_pack"]
BillingGrantMode = Literal["unlimited", "prepaid_quota"]
BillingFeatureControlMode = Literal["free", "grant_required", "blocked"]
BillingCurrency = Literal["usd"]
BillingRecurringInterval = Literal["day", "week", "month", "year"]
BillingStripeSyncMode = Literal["create", "bind_existing"]
BillingPurchaseStatus = Literal[
    "pending", "active", "expired", "canceled", "consumed", "failed"
]
BillingGrantStatus = Literal["active", "expired", "consumed", "canceled"]
BillingGrantKind = Literal["feature", "credits"]
BillingGrantRefresh = Literal["once", "per_period"]
OpenApiClientStatus = Literal["active", "disabled"]
OpenApiKeyStatus = Literal["active", "revoked"]
OpenApiKeyScope = Literal["test", "live"]


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
    """Config for prepaid quota grant mode with a fixed credits amount."""

    feature_key: str = Field(..., min_length=1, max_length=128)
    grant_mode: Literal["prepaid_quota"]
    credits: int = Field(..., gt=0)


class BillingProductConfigPrepaidQuotaCustomAmount(BillingAdminSchema):
    """Config for prepaid quota granted from a customer-chosen payment amount.

    The customer picks how much to pay; credits are derived from that amount
    instead of being a fixed number baked into the product.
    """

    feature_key: str = Field(..., min_length=1, max_length=128)
    grant_mode: Literal["prepaid_quota"]
    credits_per_currency_unit: int = Field(..., gt=0)
    min_amount_cents: int = Field(..., gt=0)
    max_amount_cents: int = Field(..., gt=0)

    @model_validator(mode="after")
    def _validate_amount_range(self) -> "BillingProductConfigPrepaidQuotaCustomAmount":
        if self.min_amount_cents > self.max_amount_cents:
            raise ValueError(
                "min_amount_cents must be less than or equal to max_amount_cents"
            )
        return self


def _config_entry_kind(value: Any) -> str:
    """Pick the config entry variant.

    `grant_mode` alone cannot discriminate here: both prepaid variants carry
    `grant_mode="prepaid_quota"`. The presence of `credits_per_currency_unit`
    is what marks the custom-amount variant.
    """
    if isinstance(value, dict):
        grant_mode = value.get("grant_mode")
        has_rate = value.get("credits_per_currency_unit") is not None
    else:
        grant_mode = getattr(value, "grant_mode", None)
        has_rate = getattr(value, "credits_per_currency_unit", None) is not None

    if grant_mode == "unlimited":
        return "unlimited"
    return "prepaid_quota_custom_amount" if has_rate else "prepaid_quota"


BillingProductConfigEntry = Annotated[
    Annotated[BillingProductConfigUnlimited, Tag("unlimited")]
    | Annotated[BillingProductConfigPrepaidQuota, Tag("prepaid_quota")]
    | Annotated[
        BillingProductConfigPrepaidQuotaCustomAmount,
        Tag("prepaid_quota_custom_amount"),
    ],
    Discriminator(_config_entry_kind),
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
]

BillingOptionalProductConfigJson = Annotated[
    list[BillingProductConfigEntry],
    BeforeValidator(_normalize_config_json_array),
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
    """GrantPreview response model.

    `granted_quantity` is set for fixed grants. Custom-amount grants leave it
    empty and describe the conversion rate and accepted range instead.
    """

    feature_key: str
    grant_mode: BillingGrantMode
    granted_quantity: int | None
    credits_per_currency_unit: int | None = None
    min_amount_cents: int | None = None
    max_amount_cents: int | None = None


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


class StripeCatalogInfoNone(BillingAdminSchema):
    """Empty Stripe catalog marker for local-only system products."""

    stripe_product_id: str = ""
    stripe_price_id: str = ""
    currency: BillingCurrency = "usd"
    unit_amount: int = 0
    billing_scheme: str = ""
    recurring_interval: BillingRecurringInterval | None = None
    recurring_interval_count: int | None = None
    lookup_key: str | None = None
    active: bool = False


class BillingProductDetail(BillingProduct):
    """Detailed BillingProduct response model."""

    grant_preview: list[GrantPreview]
    stripe_catalog: StripeCatalogInfo | None = None


class BillingProductListResponse(BillingAdminSchema):
    """Paginated list response."""

    items: list[BillingProduct]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)


class BillingFeaturePolicy(BillingAdminSchema):
    """Billing feature policy row."""

    feature_key: str = Field(..., min_length=1, max_length=128)
    control_mode: BillingFeatureControlMode
    name: str | None = None
    description: str | None = None
    active: bool
    config_json: dict
    created_at: str
    updated_at: str


class BillingFeaturePolicyListResponse(BillingAdminSchema):
    """List response for billing feature policies."""

    items: list[BillingFeaturePolicy]


class OpenApiClient(BillingAdminSchema):
    """OpenAPI client row."""

    client_id: int
    client_code: str
    name: str
    status: OpenApiClientStatus
    created_at: str
    updated_at: str


class OpenApiClientListResponse(BillingAdminSchema):
    """Paginated OpenAPI client list response."""

    items: list[OpenApiClient]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)


class OpenApiKey(BillingAdminSchema):
    """OpenAPI key metadata row. The plaintext key is not included here."""

    key_id: int
    client_id: int
    client_code: str
    client_name: str
    client_status: OpenApiClientStatus
    key_prefix: str
    secret_version: str
    status: OpenApiKeyStatus
    expires_at: str | None = None
    rpm_limit: int
    burst_limit: int
    created_at: str
    updated_at: str


class OpenApiKeyListResponse(BillingAdminSchema):
    """Paginated OpenAPI key list response."""

    items: list[OpenApiKey]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)


class OpenApiKeyCreateRequest(BillingAdminSchema):
    """Create an OpenAPI key for an existing t_openapi_client.id."""

    client_id: int = Field(..., gt=0)
    key_scope: OpenApiKeyScope = "test"
    key: str | None = Field(default=None, min_length=21)
    rpm_limit: int = Field(default=600, gt=0)
    burst_limit: int = Field(default=150, gt=0)
    expires_at: datetime | None = None
    secret_version: str = Field(default="v1", min_length=1, max_length=32)


class OpenApiKeyCreateResponse(OpenApiKey):
    """Created OpenAPI key response with one-time plaintext API key."""

    api_key: str


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
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    product_type: BillingProductType | None = None
    active: bool | None = None
    sort_order: int | None = None
    config_json: BillingOptionalProductConfigJson | None = None
    stripe_sync: BillingCreateStripeSync | None = None


class BillingUserOption(BillingAdminSchema):
    """Searchable user option for manual billing."""

    user_id: int
    email: str
    name: str | None = None
    company_name: str | None = None


class BillingUserSearchResponse(BillingAdminSchema):
    """Search response for billing users."""

    items: list[BillingUserOption]


class BillingManualGrantInput(BillingAdminSchema):
    """Manual entitlement grant input payload."""

    feature_key: str = Field(..., min_length=1, max_length=128)
    grant_mode: BillingGrantMode
    quantity: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @model_validator(mode="after")
    def validate_quantity_and_dates(self) -> "BillingManualGrantInput":
        if self.grant_mode == "prepaid_quota" and self.quantity is None:
            raise ValueError("quantity is required when grant_mode=prepaid_quota")
        if self.grant_mode == "unlimited" and self.quantity is not None:
            raise ValueError("quantity must be omitted when grant_mode=unlimited")
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at <= self.starts_at
        ):
            raise ValueError("ends_at must be after starts_at")
        return self


class BillingCreateManualPurchaseRequest(BillingAdminSchema):
    """Create admin-manual purchase request payload."""

    product_code: str = Field(..., min_length=1, max_length=64)
    purchase_starts_at: datetime | None = None
    purchase_ends_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=255)
    contract_no: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=2000)
    grants: list[BillingManualGrantInput] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_dates(self) -> "BillingCreateManualPurchaseRequest":
        if (
            self.purchase_starts_at is not None
            and self.purchase_ends_at is not None
            and self.purchase_ends_at <= self.purchase_starts_at
        ):
            raise ValueError("purchase_ends_at must be after purchase_starts_at")
        return self


class BillingGrantSnapshot(BillingAdminSchema):
    """Entitlement grant snapshot for summary responses."""

    grant_id: int
    purchase_id: int
    feature_key: str
    grant_mode: BillingGrantMode
    grant_kind: BillingGrantKind = "feature"
    granted_quantity: int | None = None
    remaining_quantity: int | None = None
    reserved_quantity: int = 0
    starts_at: str | None = None
    ends_at: str | None = None
    status: BillingGrantStatus
    config_json: dict


class BillingPurchaseSnapshot(BillingAdminSchema):
    """Purchase snapshot with child grants."""

    purchase_id: int
    product_code: str
    product_name: str
    product_family: BillingProductFamily
    purchase_type: str
    status: BillingPurchaseStatus
    purchased_at: str
    starts_at: str | None = None
    ends_at: str | None = None
    source: str | None = None
    reason: str | None = None
    contract_no: str | None = None
    note: str | None = None
    grants: list[BillingGrantSnapshot]


class BillingFeatureBalanceSummary(BillingAdminSchema):
    """Per-feature balance aggregation for a user."""

    feature_key: str
    active_unlimited: bool
    total_granted: int
    total_remaining: int


class BillingUsageEventSnapshot(BillingAdminSchema):
    """Usage event snapshot for admin inspection."""

    usage_event_id: int
    feature_key: str
    quantity: int
    usage_status: str
    created_at: str
    committed_at: str | None = None


class BillingUserBillingSummaryResponse(BillingAdminSchema):
    """Summary response for a user's billing state."""

    user: BillingUserOption
    balances: list[BillingFeatureBalanceSummary]
    purchases: list[BillingPurchaseSnapshot]
    recent_usage: list[BillingUsageEventSnapshot]


class BillingCancelManualPurchaseRequest(BillingAdminSchema):
    """Cancel admin-manual purchase payload."""

    reason: str | None = Field(default=None, max_length=255)


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
