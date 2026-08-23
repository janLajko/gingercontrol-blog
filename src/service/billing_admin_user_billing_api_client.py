"""Billing admin API layer for manual user billing operations."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import select

from src.db.base import get_billing_session_local
from src.db.models import (
    BillingEntitlementGrantRecord,
    BillingFeaturePolicyRecord,
    BillingProductRecord,
    BillingPurchaseRecord,
    BillingUsageEventRecord,
    UserRecord,
)
from src.schemas.billing_admin import (
    BillingCancelManualPurchaseRequest,
    BillingCreateManualPurchaseRequest,
    BillingFeatureBalanceSummary,
    BillingGrantSnapshot,
    BillingPurchaseSnapshot,
    BillingUsageEventSnapshot,
    BillingUserBillingSummaryResponse,
    BillingUserOption,
    BillingUserSearchResponse,
)
from src.service.billing_admin_product_api_client import BillingAdminApiException


class BillingAdminUserBillingApiClient:
    """Backend API layer for admin-manual user billing."""

    def __init__(
        self,
        *,
        session_local_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._session_local_factory = session_local_factory or get_billing_session_local

    async def search_users(
        self,
        *,
        keyword: str | None,
        limit: int,
    ) -> BillingUserSearchResponse:
        session = self._open_session()
        try:
            normalized_keyword = (keyword or "").strip()
            if not normalized_keyword:
                return BillingUserSearchResponse(items=[])

            stmt = (
                select(UserRecord)
                .where(UserRecord.email.ilike(f"%{normalized_keyword}%"))
                .order_by(UserRecord.email.asc())
                .limit(max(1, min(limit, 50)))
            )
            rows = session.execute(stmt).scalars().all()
            return BillingUserSearchResponse(
                items=[_to_user_option(row) for row in rows]
            )
        finally:
            session.close()

    async def get_user_billing_summary(
        self,
        user_id: int,
    ) -> BillingUserBillingSummaryResponse:
        session = self._open_session()
        try:
            user = self._get_user_or_raise(session, user_id)
            purchases = (
                session.execute(
                    select(BillingPurchaseRecord)
                    .where(
                        BillingPurchaseRecord.subject_type == "user",
                        BillingPurchaseRecord.subject_id == user_id,
                    )
                    .order_by(
                        BillingPurchaseRecord.purchased_at.desc(),
                        BillingPurchaseRecord.id.desc(),
                    )
                )
                .scalars()
                .all()
            )
            purchase_ids = [purchase.id for purchase in purchases]

            grants = (
                session.execute(
                    select(BillingEntitlementGrantRecord)
                    .where(BillingEntitlementGrantRecord.purchase_id.in_(purchase_ids))
                    .order_by(
                        BillingEntitlementGrantRecord.created_at.desc(),
                        BillingEntitlementGrantRecord.id.desc(),
                    )
                )
                .scalars()
                .all()
                if purchase_ids
                else []
            )
            grants_by_purchase: dict[int, list[BillingEntitlementGrantRecord]] = defaultdict(list)
            for grant in grants:
                grants_by_purchase[grant.purchase_id].append(grant)

            product_codes = sorted({purchase.product_code for purchase in purchases})
            products = (
                session.execute(
                    select(BillingProductRecord).where(
                        BillingProductRecord.product_code.in_(product_codes)
                    )
                )
                .scalars()
                .all()
                if product_codes
                else []
            )
            product_by_code = {product.product_code: product for product in products}

            usage_rows = (
                session.execute(
                    select(BillingUsageEventRecord)
                    .where(
                        BillingUsageEventRecord.subject_type == "user",
                        BillingUsageEventRecord.subject_id == user_id,
                    )
                    .order_by(
                        BillingUsageEventRecord.created_at.desc(),
                        BillingUsageEventRecord.id.desc(),
                    )
                    .limit(20)
                )
                .scalars()
                .all()
            )

            return BillingUserBillingSummaryResponse(
                user=_to_user_option(user),
                balances=_build_balance_summary(grants),
                purchases=[
                    _to_purchase_snapshot(
                        purchase,
                        product=product_by_code.get(purchase.product_code),
                        grants=grants_by_purchase.get(purchase.id, []),
                    )
                    for purchase in purchases
                ],
                recent_usage=[_to_usage_snapshot(row) for row in usage_rows],
            )
        finally:
            session.close()

    async def create_manual_purchase(
        self,
        *,
        user_id: int,
        payload: BillingCreateManualPurchaseRequest,
    ) -> BillingPurchaseSnapshot:
        session = self._open_session()
        try:
            user = self._get_user_or_raise(session, user_id)
            product = self._get_product_or_raise(session, payload.product_code)
            if not product.active:
                raise BillingAdminApiException(
                    status_code=422,
                    code="product_inactive",
                    message=f"billing product is inactive: {product.product_code}",
                    field_errors={"product_code": "inactive"},
                )

            feature_keys = sorted({grant.feature_key for grant in payload.grants})
            policy_rows = (
                session.execute(
                    select(BillingFeaturePolicyRecord).where(
                        BillingFeaturePolicyRecord.feature_key.in_(feature_keys)
                    )
                )
                .scalars()
                .all()
            )
            policies = {row.feature_key: row for row in policy_rows}

            now = _utcnow()
            self._validate_manual_grants(
                payload=payload,
                policies=policies,
            )

            purchase = BillingPurchaseRecord(
                subject_type="user",
                subject_id=user.id,
                product_code=product.product_code,
                # Manual purchases never go through Stripe, so they carry their
                # own type regardless of whether the product is a subscription.
                purchase_type="one_time_ginger",
                stripe_checkout_session_id=None,
                stripe_subscription_id=None,
                stripe_price_id=product.stripe_price_id,
                status=_resolve_purchase_status(
                    starts_at=payload.purchase_starts_at,
                    ends_at=payload.purchase_ends_at,
                    now=now,
                ),
                purchased_at=now,
                starts_at=payload.purchase_starts_at,
                ends_at=payload.purchase_ends_at,
                raw_payload={
                    "source": "admin_manual",
                    "reason": payload.reason,
                    "contract_no": payload.contract_no,
                    "note": payload.note,
                },
                created_at=now,
                updated_at=now,
            )
            session.add(purchase)
            session.flush()

            grant_records: list[BillingEntitlementGrantRecord] = []
            for grant in payload.grants:
                granted_quantity = (
                    grant.quantity if grant.grant_mode == "prepaid_quota" else None
                )
                grant_records.append(
                    BillingEntitlementGrantRecord(
                        purchase_id=purchase.id,
                        subject_type="user",
                        subject_id=user.id,
                        feature_key=grant.feature_key,
                        grant_mode=grant.grant_mode,
                        grant_kind=_resolve_grant_kind(grant.feature_key),
                        granted_quantity=granted_quantity,
                        remaining_quantity=granted_quantity,
                        reserved_quantity=0,
                        period_key=None,
                        starts_at=grant.starts_at,
                        ends_at=grant.ends_at,
                        status=_resolve_grant_status(
                            ends_at=grant.ends_at,
                            now=now,
                        ),
                        config_json=_grant_config_dict(grant),
                        created_at=now,
                        updated_at=now,
                    )
                )

            session.add_all(grant_records)
            session.commit()
            session.refresh(purchase)
            for grant_record in grant_records:
                session.refresh(grant_record)

            return _to_purchase_snapshot(
                purchase,
                product=product,
                grants=grant_records,
            )
        except BillingAdminApiException:
            session.rollback()
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def cancel_manual_purchase(
        self,
        *,
        purchase_id: int,
        payload: BillingCancelManualPurchaseRequest,
    ) -> BillingPurchaseSnapshot:
        session = self._open_session()
        try:
            purchase = self._get_purchase_or_raise(session, purchase_id)
            raw_payload = dict(purchase.raw_payload or {})
            if raw_payload.get("source") != "admin_manual":
                raise BillingAdminApiException(
                    status_code=409,
                    code="purchase_not_cancelable",
                    message="only admin_manual purchases can be canceled",
                )
            if purchase.status == "canceled":
                raise BillingAdminApiException(
                    status_code=409,
                    code="purchase_already_canceled",
                    message="purchase is already canceled",
                )

            now = _utcnow()
            purchase.status = "canceled"
            purchase.updated_at = now
            purchase.raw_payload = {
                **raw_payload,
                "canceled_reason": payload.reason,
                "canceled_at": _to_rfc3339(now),
            }

            grants = (
                session.execute(
                    select(BillingEntitlementGrantRecord)
                    .where(BillingEntitlementGrantRecord.purchase_id == purchase_id)
                    .order_by(BillingEntitlementGrantRecord.id.desc())
                )
                .scalars()
                .all()
            )
            for grant in grants:
                if grant.status in {"canceled", "consumed"}:
                    continue
                grant.status = "canceled"
                grant.updated_at = now
                grant.config_json = {
                    **dict(grant.config_json or {}),
                    "canceled_reason": payload.reason,
                }

            product = self._get_product_or_raise(session, purchase.product_code)
            session.commit()
            session.refresh(purchase)
            for grant in grants:
                session.refresh(grant)

            return _to_purchase_snapshot(
                purchase,
                product=product,
                grants=grants,
            )
        except BillingAdminApiException:
            session.rollback()
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _open_session(self):
        session_local = self._session_local_factory()
        if session_local is None:
            raise BillingAdminApiException(
                status_code=500,
                code="database_not_configured",
                message="BILLING_DATABASE_URL is not configured",
            )
        return session_local()

    def _get_user_or_raise(self, session: Any, user_id: int) -> UserRecord:
        row = session.execute(
            select(UserRecord).where(UserRecord.id == user_id)
        ).scalar_one_or_none()
        if row is None:
            raise BillingAdminApiException(
                status_code=404,
                code="user_not_found",
                message=f"user not found: {user_id}",
            )
        return row

    def _get_product_or_raise(self, session: Any, product_code: str) -> BillingProductRecord:
        row = session.execute(
            select(BillingProductRecord).where(
                BillingProductRecord.product_code == product_code
            )
        ).scalar_one_or_none()
        if row is None:
            raise BillingAdminApiException(
                status_code=404,
                code="product_not_found",
                message=f"billing product not found: {product_code}",
            )
        return row

    def _get_purchase_or_raise(self, session: Any, purchase_id: int) -> BillingPurchaseRecord:
        row = session.execute(
            select(BillingPurchaseRecord).where(BillingPurchaseRecord.id == purchase_id)
        ).scalar_one_or_none()
        if row is None:
            raise BillingAdminApiException(
                status_code=404,
                code="purchase_not_found",
                message=f"billing purchase not found: {purchase_id}",
            )
        return row

    def _validate_manual_grants(
        self,
        *,
        payload: BillingCreateManualPurchaseRequest,
        policies: dict[str, BillingFeaturePolicyRecord],
    ) -> None:
        for index, grant in enumerate(payload.grants):
            policy = policies.get(grant.feature_key)
            if policy is None:
                raise BillingAdminApiException(
                    status_code=422,
                    code="feature_key_invalid",
                    message=f"feature_key not found: {grant.feature_key}",
                    field_errors={f"grants.{index}.feature_key": "not_found"},
                )
            if not policy.active:
                raise BillingAdminApiException(
                    status_code=422,
                    code="feature_key_inactive",
                    message=f"feature_key is inactive: {grant.feature_key}",
                    field_errors={f"grants.{index}.feature_key": "inactive"},
                )
            if payload.purchase_starts_at is not None and grant.starts_at is not None:
                if grant.starts_at < payload.purchase_starts_at:
                    raise BillingAdminApiException(
                        status_code=422,
                        code="grant_window_invalid",
                        message="grant starts_at must be within purchase window",
                        field_errors={f"grants.{index}.starts_at": "before_purchase"},
                    )
            if payload.purchase_ends_at is not None and grant.ends_at is not None:
                if grant.ends_at > payload.purchase_ends_at:
                    raise BillingAdminApiException(
                        status_code=422,
                        code="grant_window_invalid",
                        message="grant ends_at must be within purchase window",
                        field_errors={f"grants.{index}.ends_at": "after_purchase"},
                    )
            if payload.purchase_starts_at is not None and grant.starts_at is None:
                grant.starts_at = payload.purchase_starts_at
            if payload.purchase_ends_at is not None and grant.ends_at is None:
                grant.ends_at = payload.purchase_ends_at


def _to_user_option(row: UserRecord) -> BillingUserOption:
    return BillingUserOption(
        user_id=row.id,
        email=row.email,
        name=row.name,
        company_name=row.company_name,
    )


def _to_purchase_snapshot(
    purchase: BillingPurchaseRecord,
    *,
    product: BillingProductRecord | None,
    grants: list[BillingEntitlementGrantRecord],
) -> BillingPurchaseSnapshot:
    raw_payload = dict(purchase.raw_payload or {})
    return BillingPurchaseSnapshot(
        purchase_id=purchase.id,
        product_code=purchase.product_code,
        product_name=product.name if product is not None else purchase.product_code,
        product_family=(product.product_family if product is not None else "system"),
        purchase_type=purchase.purchase_type,
        status=purchase.status,
        purchased_at=_to_rfc3339(purchase.purchased_at),
        starts_at=_to_optional_rfc3339(purchase.starts_at),
        ends_at=_to_optional_rfc3339(purchase.ends_at),
        source=raw_payload.get("source"),
        reason=raw_payload.get("reason"),
        contract_no=raw_payload.get("contract_no"),
        note=raw_payload.get("note"),
        grants=[_to_grant_snapshot(grant) for grant in grants],
    )


def _to_grant_snapshot(grant: BillingEntitlementGrantRecord) -> BillingGrantSnapshot:
    return BillingGrantSnapshot(
        grant_id=grant.id,
        purchase_id=grant.purchase_id,
        feature_key=grant.feature_key,
        grant_mode=grant.grant_mode,
        grant_kind=grant.grant_kind,
        granted_quantity=grant.granted_quantity,
        remaining_quantity=grant.remaining_quantity,
        reserved_quantity=grant.reserved_quantity,
        starts_at=_to_optional_rfc3339(grant.starts_at),
        ends_at=_to_optional_rfc3339(grant.ends_at),
        status=grant.status,
        config_json=dict(grant.config_json or {}),
    )


def _to_usage_snapshot(row: BillingUsageEventRecord) -> BillingUsageEventSnapshot:
    return BillingUsageEventSnapshot(
        usage_event_id=row.id,
        feature_key=row.feature_key,
        quantity=row.quantity,
        usage_status=row.usage_status,
        created_at=_to_rfc3339(row.created_at),
        committed_at=_to_optional_rfc3339(row.committed_at),
    )


def _build_balance_summary(
    grants: list[BillingEntitlementGrantRecord],
) -> list[BillingFeatureBalanceSummary]:
    now = _utcnow()
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "active_unlimited": False,
            "total_granted": 0,
            "total_remaining": 0,
        }
    )
    for grant in grants:
        if not _is_effective_grant(grant, now=now):
            continue
        bucket = grouped[grant.feature_key]
        if grant.grant_mode == "unlimited":
            bucket["active_unlimited"] = True
        if grant.granted_quantity is not None:
            bucket["total_granted"] += int(grant.granted_quantity)
        if grant.remaining_quantity is not None:
            bucket["total_remaining"] += int(grant.remaining_quantity)

    return [
        BillingFeatureBalanceSummary(
            feature_key=feature_key,
            active_unlimited=values["active_unlimited"],
            total_granted=values["total_granted"],
            total_remaining=values["total_remaining"],
        )
        for feature_key, values in sorted(grouped.items())
    ]


CREDITS_FEATURE_KEY = "credits.balance"


def _resolve_grant_kind(feature_key: str) -> str:
    """Credits land in the wallet; everything else is a per-feature entitlement."""
    return "credits" if feature_key == CREDITS_FEATURE_KEY else "feature"


def _grant_config_dict(grant) -> dict[str, Any]:
    payload = {
        "feature_key": grant.feature_key,
        "grant_mode": grant.grant_mode,
        "grant_kind": _resolve_grant_kind(grant.feature_key),
        # Manual grants are one-off: an admin issuing them again is an explicit
        # act, never something a subscription period should replay.
        "refresh": "once",
    }
    if grant.quantity is not None:
        payload["credits"] = grant.quantity
    return payload


def _resolve_purchase_status(
    *,
    starts_at: datetime | None,
    ends_at: datetime | None,
    now: datetime,
) -> str:
    if starts_at is not None and starts_at > now:
        return "pending"
    if ends_at is not None and ends_at <= now:
        return "expired"
    return "active"


def _resolve_grant_status(
    *,
    ends_at: datetime | None,
    now: datetime,
) -> str:
    if ends_at is not None and ends_at <= now:
        return "expired"
    return "active"


def _is_effective_grant(
    grant: BillingEntitlementGrantRecord,
    *,
    now: datetime,
) -> bool:
    if grant.status != "active":
        return False
    if grant.starts_at is not None and grant.starts_at > now:
        return False
    if grant.ends_at is not None and grant.ends_at <= now:
        return False
    return True


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_optional_rfc3339(value: datetime | None) -> str | None:
    return _to_rfc3339(value) if value is not None else None


_billing_admin_user_billing_api_client = BillingAdminUserBillingApiClient()


def get_billing_admin_user_billing_api_client() -> BillingAdminUserBillingApiClient:
    """Return the default billing admin user billing API layer instance."""

    return _billing_admin_user_billing_api_client
