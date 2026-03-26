"""Billing admin product API layer with local persistence and Stripe sync."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from src.db.base import get_billing_session_local
from src.db.models import BillingProductRecord
from src.schemas.billing_admin import (
    BillingCreateProductRequest,
    BillingPatchProductRequest,
    BillingProduct,
    BillingProductConfigJson,
    BillingProductDetail,
    BillingProductFamily,
    BillingProductListResponse,
    BillingSyncStripeRequest,
    BillingSyncStripeResponse,
    BillingUpdateProductRequest,
    GrantPreview,
    StripeCatalogInfo,
)
from src.service.stripe_billing_gateway import (
    StripeBillingGateway,
    StripeGatewayError,
)


@dataclass(slots=True)
class BillingAdminApiException(Exception):
    """Billing admin exception translated to the OpenAPI error shape."""

    status_code: int
    code: str
    message: str
    field_errors: dict[str, str] | None = None


class BillingAdminProductApiClient:
    """Backend API layer for billing admin product operations."""

    def __init__(
        self,
        *,
        session_local_factory: Callable[[], Any] | None = None,
        stripe_gateway: StripeBillingGateway | None = None,
    ) -> None:
        self._session_local_factory = session_local_factory or get_billing_session_local
        self._stripe_gateway = stripe_gateway or StripeBillingGateway()

    async def list_products(
        self,
        *,
        product_family: BillingProductFamily | None,
        active: bool | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> BillingProductListResponse:
        session = self._open_session()
        try:
            stmt = select(BillingProductRecord)
            count_stmt = select(func.count()).select_from(BillingProductRecord)

            if product_family is not None:
                stmt = stmt.where(BillingProductRecord.product_family == product_family)
                count_stmt = count_stmt.where(
                    BillingProductRecord.product_family == product_family
                )

            if active is not None:
                stmt = stmt.where(BillingProductRecord.active == active)
                count_stmt = count_stmt.where(BillingProductRecord.active == active)

            normalized_keyword = (keyword or "").strip()
            if normalized_keyword:
                pattern = f"%{normalized_keyword}%"
                predicate = or_(
                    BillingProductRecord.product_code.ilike(pattern),
                    BillingProductRecord.name.ilike(pattern),
                )
                stmt = stmt.where(predicate)
                count_stmt = count_stmt.where(predicate)

            stmt = stmt.order_by(
                BillingProductRecord.sort_order.asc(),
                BillingProductRecord.updated_at.desc(),
                BillingProductRecord.product_code.asc(),
            )
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)

            rows = session.execute(stmt).scalars().all()
            total = int(session.execute(count_stmt).scalar_one() or 0)
            items: list[BillingProduct] = []
            for row in rows:
                items.append(await self._to_billing_product_response(row))

            return BillingProductListResponse(
                items=items,
                page=page,
                page_size=page_size,
                total=total,
            )
        finally:
            session.close()

    async def get_product(self, product_code: str) -> BillingProductDetail:
        session = self._open_session()
        try:
            record = self._get_product_or_raise(session, product_code)
            stripe_product, stripe_price = await self._retrieve_stripe_state(record)
            return self._to_billing_product_detail_response(
                record,
                stripe_product,
                stripe_price,
            )
        finally:
            session.close()

    async def create_product(self, payload: BillingCreateProductRequest) -> BillingProduct:
        self._validate_create_payload(payload)
        session = self._open_session()
        try:
            existing = session.execute(
                select(BillingProductRecord).where(
                    BillingProductRecord.product_code == payload.product_code
                )
            ).scalar_one_or_none()
            if existing is not None:
                raise BillingAdminApiException(
                    status_code=409,
                    code="product_code_conflict",
                    message=f"product_code already exists: {payload.product_code}",
                    field_errors={"product_code": "already_exists"},
                )

            stripe_product_id: str
            stripe_price_id: str
            if payload.stripe_sync.mode == "create":
                stripe_product, stripe_price = await self._create_stripe_objects(payload)
                stripe_product_id = str(stripe_product["id"])
                stripe_price_id = str(stripe_price["id"])
            else:
                stripe_product, stripe_price = await self._validate_bound_stripe_objects(
                    stripe_product_id=payload.stripe_sync.stripe_product_id,
                    stripe_price_id=payload.stripe_sync.stripe_price_id,
                    product_type=payload.product_type,
                )
                stripe_product_id = str(stripe_product["id"])
                stripe_price_id = str(stripe_price["id"])

            now = datetime.utcnow()
            record = BillingProductRecord(
                product_code=payload.product_code,
                product_family=payload.product_family,
                name=payload.name,
                description=payload.description,
                product_type=payload.product_type,
                stripe_product_id=stripe_product_id,
                stripe_price_id=stripe_price_id,
                active=payload.active,
                sort_order=payload.sort_order,
                config_json=_config_json_dict(payload.config_json),
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return await self._to_billing_product_response(record)
        except IntegrityError as exc:
            session.rollback()
            raise BillingAdminApiException(
                status_code=409,
                code="product_code_conflict",
                message=f"product_code already exists: {payload.product_code}",
                field_errors={"product_code": "already_exists"},
            ) from exc
        except BillingAdminApiException:
            session.rollback()
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def replace_product(
        self,
        product_code: str,
        payload: BillingUpdateProductRequest,
    ) -> BillingProductDetail:
        session = self._open_session()
        try:
            record = self._get_product_or_raise(session, product_code)
            self._validate_update_payload(payload, product_type=record.product_type)

            await self._sync_stripe_product(
                stripe_product_id=_require_stripe_binding(
                    record.stripe_product_id,
                    field_name="stripe_product_id",
                ),
                name=payload.name,
                description=payload.description,
                active=payload.active,
                product_code=record.product_code,
                product_family=record.product_family,
                product_type=record.product_type,
            )

            if (
                payload.stripe_sync.price_change is not None
                and payload.stripe_sync.price_change.enabled
            ):
                new_price = await self._create_stripe_price(
                    stripe_product_id=record.stripe_product_id,
                    active=payload.active,
                    product_code=record.product_code,
                    config_json=payload.config_json,
                    price_payload=payload.stripe_sync.price_change.model_dump(
                        exclude_none=True
                    ),
                )
                if record.stripe_price_id != str(new_price["id"]):
                    await self._deactivate_previous_price(
                        _require_stripe_binding(
                            record.stripe_price_id,
                            field_name="stripe_price_id",
                        )
                    )
                record.stripe_price_id = str(new_price["id"])
            else:
                await self._sync_stripe_price_metadata(
                    stripe_price_id=_require_stripe_binding(
                        record.stripe_price_id,
                        field_name="stripe_price_id",
                    ),
                    active=payload.active,
                    product_code=record.product_code,
                    config_json=payload.config_json,
                )

            record.name = payload.name
            record.description = payload.description
            record.active = payload.active
            record.sort_order = payload.sort_order
            record.config_json = _config_json_dict(payload.config_json)
            record.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(record)

            stripe_product, stripe_price = await self._retrieve_stripe_state(record)
            return self._to_billing_product_detail_response(
                record,
                stripe_product,
                stripe_price,
            )
        except BillingAdminApiException:
            session.rollback()
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def patch_product(
        self,
        product_code: str,
        payload: BillingPatchProductRequest,
    ) -> BillingProduct:
        session = self._open_session()
        try:
            record = self._get_product_or_raise(session, product_code)
            await self._sync_stripe_product(
                stripe_product_id=_require_stripe_binding(
                    record.stripe_product_id,
                    field_name="stripe_product_id",
                ),
                name=record.name,
                description=record.description,
                active=payload.active,
                product_code=record.product_code,
                product_family=record.product_family,
                product_type=record.product_type,
            )
            await self._sync_stripe_price_metadata(
                stripe_price_id=_require_stripe_binding(
                    record.stripe_price_id,
                    field_name="stripe_price_id",
                ),
                active=payload.active,
                product_code=record.product_code,
                config_json=_normalize_config_json_entries(record.config_json),
            )

            record.active = payload.active
            record.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(record)
            return await self._to_billing_product_response(record)
        except BillingAdminApiException:
            session.rollback()
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def sync_stripe(
        self,
        product_code: str,
        payload: BillingSyncStripeRequest,
    ) -> BillingSyncStripeResponse:
        session = self._open_session()
        try:
            record = self._get_product_or_raise(session, product_code)

            if payload.sync_product:
                await self._sync_stripe_product(
                    stripe_product_id=_require_stripe_binding(
                        record.stripe_product_id,
                        field_name="stripe_product_id",
                    ),
                    name=record.name,
                    description=record.description,
                    active=record.active,
                    product_code=record.product_code,
                    product_family=record.product_family,
                    product_type=record.product_type,
                )

            if payload.sync_price:
                await self._sync_stripe_price_metadata(
                    stripe_price_id=_require_stripe_binding(
                        record.stripe_price_id,
                        field_name="stripe_price_id",
                    ),
                    active=record.active,
                    product_code=record.product_code,
                    config_json=_normalize_config_json_entries(record.config_json),
                )

            return BillingSyncStripeResponse(
                ok=True,
                product_code=record.product_code,
                stripe_product_id=_require_stripe_binding(
                    record.stripe_product_id,
                    field_name="stripe_product_id",
                ),
                stripe_price_id=_require_stripe_binding(
                    record.stripe_price_id,
                    field_name="stripe_price_id",
                ),
            )
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

    def _get_product_or_raise(self, session: Any, product_code: str) -> BillingProductRecord:
        record = session.execute(
            select(BillingProductRecord).where(
                BillingProductRecord.product_code == product_code
            )
        ).scalar_one_or_none()
        if record is None:
            raise BillingAdminApiException(
                status_code=404,
                code="product_not_found",
                message=f"billing product not found: {product_code}",
            )
        return record

    def _validate_create_payload(self, payload: BillingCreateProductRequest) -> None:
        if payload.stripe_sync.mode == "create":
            _validate_price_type_against_product_type(
                product_type=payload.product_type,
                price_type=payload.stripe_sync.price.type,
                field_name="stripe_sync.price.type",
            )

    def _validate_update_payload(
        self,
        payload: BillingUpdateProductRequest,
        *,
        product_type: str,
    ) -> None:
        if (
            payload.stripe_sync.price_change is not None
            and payload.stripe_sync.price_change.enabled
        ):
            _validate_price_type_against_product_type(
                product_type=product_type,
                price_type=payload.stripe_sync.price_change.type,
                field_name="stripe_sync.price_change.type",
            )

    async def _to_billing_product_response(
        self,
        record: BillingProductRecord,
    ) -> BillingProduct:
        config_json = await self._resolve_config_json(record)
        return BillingProduct(
            product_code=record.product_code,
            product_family=record.product_family,
            name=record.name,
            description=record.description,
            product_type=record.product_type,
            stripe_product_id=record.stripe_product_id or "",
            stripe_price_id=record.stripe_price_id or "",
            active=record.active,
            sort_order=record.sort_order,
            config_json=config_json,
            created_at=_to_rfc3339(record.created_at),
            updated_at=_to_rfc3339(record.updated_at),
        )

    def _to_billing_product_detail_response(
        self,
        record: BillingProductRecord,
        stripe_product: dict[str, Any],
        stripe_price: dict[str, Any],
    ) -> BillingProductDetail:
        config_json = self._resolve_config_json_from_sources(
            record,
            stripe_price=stripe_price,
        )
        return BillingProductDetail(
            product_code=record.product_code,
            product_family=record.product_family,
            name=record.name,
            description=record.description,
            product_type=record.product_type,
            stripe_product_id=record.stripe_product_id or "",
            stripe_price_id=record.stripe_price_id or "",
            active=record.active,
            sort_order=record.sort_order,
            config_json=config_json,
            grant_preview=_grant_preview_from_config(config_json),
            stripe_catalog=_to_stripe_catalog_info(stripe_product, stripe_price),
            created_at=_to_rfc3339(record.created_at),
            updated_at=_to_rfc3339(record.updated_at),
        )

    async def _resolve_config_json(
        self,
        record: BillingProductRecord,
    ) -> BillingProductConfigJson:
        config_json = _normalize_config_json_entries(record.config_json)
        if _is_config_json_candidate_valid(config_json):
            return _validate_config_json_payload(
                config_json,
                product_code=record.product_code,
            )

        stripe_price: dict[str, Any] | None = None
        if record.stripe_price_id:
            try:
                stripe_price = await self._stripe_gateway.retrieve_price(record.stripe_price_id)
            except StripeGatewayError:
                stripe_price = None

        return self._resolve_config_json_from_sources(record, stripe_price=stripe_price)

    def _resolve_config_json_from_sources(
        self,
        record: BillingProductRecord,
        *,
        stripe_price: dict[str, Any] | None,
    ) -> BillingProductConfigJson:
        normalized = _normalize_config_json_entries(record.config_json)
        metadata = stripe_price.get("metadata") if isinstance(stripe_price, dict) else None
        metadata = metadata if isinstance(metadata, dict) else {}

        if not normalized and metadata.get("feature_key") and metadata.get("grant_mode"):
            fallback_item: dict[str, Any] = {
                "feature_key": metadata["feature_key"],
                "grant_mode": metadata["grant_mode"],
            }
            if metadata.get("credits") not in (None, ""):
                fallback_item["credits"] = _normalize_optional_int(metadata.get("credits"))
            normalized = [fallback_item]

        return _validate_config_json_payload(
            normalized,
            product_code=record.product_code,
        )

    async def _create_stripe_objects(
        self,
        payload: BillingCreateProductRequest,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            stripe_product = await self._stripe_gateway.create_product(
                name=payload.stripe_sync.product_name or payload.name,
                description=payload.description,
                active=payload.active,
                metadata=_stripe_product_metadata(
                    product_code=payload.product_code,
                    product_family=payload.product_family,
                    product_type=payload.product_type,
                ),
            )
            stripe_price = await self._stripe_gateway.create_price(
                product_id=str(stripe_product["id"]),
                active=payload.active,
                metadata=_stripe_price_metadata(
                    product_code=payload.product_code,
                    config_json=payload.config_json,
                ),
                payload=payload.stripe_sync.price.model_dump(exclude_none=True),
            )
            return stripe_product, stripe_price
        except StripeGatewayError as exc:
            raise BillingAdminApiException(
                status_code=502,
                code="stripe_sync_failed",
                message=str(exc),
            ) from exc

    async def _validate_bound_stripe_objects(
        self,
        *,
        stripe_product_id: str,
        stripe_price_id: str,
        product_type: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            stripe_product = await self._stripe_gateway.retrieve_product(stripe_product_id)
            stripe_price = await self._stripe_gateway.retrieve_price(stripe_price_id)
        except StripeGatewayError as exc:
            raise BillingAdminApiException(
                status_code=422,
                code="stripe_binding_invalid",
                message=str(exc),
                field_errors={
                    "stripe_sync.stripe_product_id": "invalid"
                    if stripe_product_id
                    else "required",
                    "stripe_sync.stripe_price_id": "invalid"
                    if stripe_price_id
                    else "required",
                },
            ) from exc

        price_product_id = _price_product_id(stripe_price)
        if price_product_id != stripe_product_id:
            raise BillingAdminApiException(
                status_code=422,
                code="stripe_binding_invalid",
                message="Stripe Price does not belong to the provided Stripe Product",
                field_errors={"stripe_sync.stripe_price_id": "product_mismatch"},
            )

        expected_price_type = "recurring" if product_type == "subscription" else "one_time"
        actual_price_type = str(stripe_price.get("type") or "")
        if actual_price_type != expected_price_type:
            raise BillingAdminApiException(
                status_code=422,
                code="stripe_binding_invalid",
                message="Stripe Price type does not match local product_type",
                field_errors={"stripe_sync.stripe_price_id": "type_mismatch"},
            )

        return stripe_product, stripe_price

    async def _retrieve_stripe_state(
        self,
        record: BillingProductRecord,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            stripe_product = await self._stripe_gateway.retrieve_product(
                _require_stripe_binding(
                    record.stripe_product_id,
                    field_name="stripe_product_id",
                )
            )
            stripe_price = await self._stripe_gateway.retrieve_price(
                _require_stripe_binding(
                    record.stripe_price_id,
                    field_name="stripe_price_id",
                )
            )
            return stripe_product, stripe_price
        except StripeGatewayError as exc:
            raise BillingAdminApiException(
                status_code=502,
                code="stripe_sync_failed",
                message=str(exc),
            ) from exc

    async def _sync_stripe_product(
        self,
        *,
        stripe_product_id: str,
        name: str,
        description: str | None,
        active: bool,
        product_code: str,
        product_family: str,
        product_type: str,
    ) -> dict[str, Any]:
        try:
            return await self._stripe_gateway.update_product(
                stripe_product_id,
                name=name,
                description=description,
                active=active,
                metadata=_stripe_product_metadata(
                    product_code=product_code,
                    product_family=product_family,
                    product_type=product_type,
                ),
            )
        except StripeGatewayError as exc:
            raise BillingAdminApiException(
                status_code=502,
                code="stripe_sync_failed",
                message=str(exc),
            ) from exc

    async def _create_stripe_price(
        self,
        *,
        stripe_product_id: str,
        active: bool,
        product_code: str,
        config_json: BillingProductConfigJson,
        price_payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            return await self._stripe_gateway.create_price(
                product_id=stripe_product_id,
                active=active,
                metadata=_stripe_price_metadata(
                    product_code=product_code,
                    config_json=config_json,
                ),
                payload=price_payload,
            )
        except StripeGatewayError as exc:
            raise BillingAdminApiException(
                status_code=502,
                code="stripe_sync_failed",
                message=str(exc),
            ) from exc

    async def _sync_stripe_price_metadata(
        self,
        *,
        stripe_price_id: str,
        active: bool,
        product_code: str,
        config_json: BillingProductConfigJson,
    ) -> dict[str, Any]:
        try:
            return await self._stripe_gateway.update_price(
                stripe_price_id,
                active=active,
                metadata=_stripe_price_metadata(
                    product_code=product_code,
                    config_json=config_json,
                ),
            )
        except StripeGatewayError as exc:
            raise BillingAdminApiException(
                status_code=502,
                code="stripe_sync_failed",
                message=str(exc),
            ) from exc

    async def _deactivate_previous_price(self, stripe_price_id: str) -> None:
        try:
            await self._stripe_gateway.update_price(
                stripe_price_id,
                active=False,
                metadata={},
            )
        except StripeGatewayError as exc:
            raise BillingAdminApiException(
                status_code=502,
                code="stripe_sync_failed",
                message=str(exc),
            ) from exc


CONFIG_JSON_ADAPTER = TypeAdapter(BillingProductConfigJson)


def _to_stripe_catalog_info(
    stripe_product: dict[str, Any],
    stripe_price: dict[str, Any],
) -> StripeCatalogInfo:
    recurring = stripe_price.get("recurring") or {}
    return StripeCatalogInfo(
        stripe_product_id=str(stripe_product["id"]),
        stripe_price_id=str(stripe_price["id"]),
        currency=str(stripe_price.get("currency") or "usd"),
        unit_amount=int(stripe_price.get("unit_amount") or 0),
        billing_scheme=str(stripe_price.get("billing_scheme") or ""),
        recurring_interval=recurring.get("interval"),
        recurring_interval_count=recurring.get("interval_count"),
        lookup_key=stripe_price.get("lookup_key"),
        active=bool(stripe_product.get("active")) and bool(stripe_price.get("active")),
    )


def _grant_preview_from_config(
    config_json: BillingProductConfigJson | list[dict[str, Any]] | dict[str, Any],
) -> list[GrantPreview]:
    previews: list[GrantPreview] = []
    for item in _normalize_config_json_entries(config_json):
        previews.append(
            GrantPreview(
                feature_key=str(item.get("feature_key") or ""),
                grant_mode=str(item.get("grant_mode") or ""),
                granted_quantity=_normalize_optional_int(item.get("credits")),
            )
        )
    return previews


def _stripe_product_metadata(
    *,
    product_code: str,
    product_family: str,
    product_type: str,
) -> dict[str, str | None]:
    return {
        "product_code": product_code,
        "product_family": product_family,
        "product_type": product_type,
    }


def _stripe_price_metadata(
    *,
    product_code: str,
    config_json: BillingProductConfigJson | list[dict[str, Any]] | dict[str, Any],
) -> dict[str, str | None]:
    normalized = _normalize_config_json_entries(config_json)
    metadata: dict[str, str | None] = {
        "product_code": product_code,
    }

    # TODO: Multi-grant Stripe metadata mapping is not defined in the current
    # billing_stripe_mapping.md contract. Preserve legacy single-grant metadata
    # only when config_json contains exactly one entry.
    if len(normalized) == 1:
        entry = normalized[0]
        metadata["feature_key"] = str(entry.get("feature_key") or "")
        metadata["grant_mode"] = str(entry.get("grant_mode") or "")
        metadata["credits"] = (
            None
            if entry.get("credits") is None
            else str(_normalize_optional_int(entry.get("credits")))
        )

    return metadata


def _config_json_dict(config_json: BillingProductConfigJson) -> list[dict[str, Any]]:
    return [entry.model_dump(exclude_none=True) for entry in config_json]


def _normalize_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_config_json_candidate_valid(config_json: Any) -> bool:
    if not isinstance(config_json, list) or len(config_json) == 0:
        return False
    return all(isinstance(item, dict) and bool(item.get("grant_mode")) for item in config_json)


def _validate_config_json_payload(
    config_json: list[dict[str, Any]] | dict[str, Any],
    *,
    product_code: str,
) -> BillingProductConfigJson:
    try:
        return CONFIG_JSON_ADAPTER.validate_python(config_json)
    except ValidationError as exc:
        raise BillingAdminApiException(
            status_code=500,
            code="validation_error",
            message=f"billing product config_json is invalid: {product_code}",
            field_errors={"config_json": "invalid"},
        ) from exc


def _normalize_config_json_entries(
    config_json: BillingProductConfigJson | list[dict[str, Any]] | dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if config_json is None:
        return []

    if isinstance(config_json, list):
        normalized: list[dict[str, Any]] = []
        for item in config_json:
            if hasattr(item, "model_dump"):
                normalized.append(item.model_dump(exclude_none=True))
            elif isinstance(item, dict):
                normalized.append(dict(item))
        return normalized

    if hasattr(config_json, "model_dump"):
        return [config_json.model_dump(exclude_none=True)]

    if isinstance(config_json, dict):
        return [dict(config_json)]

    return []


def _require_stripe_binding(value: str | None, *, field_name: str) -> str:
    if value:
        return value
    raise BillingAdminApiException(
        status_code=502,
        code="stripe_sync_failed",
        message=f"{field_name} is not set for billing product",
    )


def _price_product_id(stripe_price: dict[str, Any]) -> str | None:
    product_value = stripe_price.get("product")
    if isinstance(product_value, str):
        return product_value
    if isinstance(product_value, dict):
        product_id = product_value.get("id")
        return str(product_id) if product_id else None
    return None


def _validate_price_type_against_product_type(
    *,
    product_type: str,
    price_type: str,
    field_name: str,
) -> None:
    expected_price_type = "recurring" if product_type == "subscription" else "one_time"
    if price_type != expected_price_type:
        raise BillingAdminApiException(
            status_code=400,
            code="validation_error",
            message=f"{field_name} does not match product_type",
            field_errors={field_name: f"must_be_{expected_price_type}"},
        )


def _to_rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


_billing_admin_product_api_client = BillingAdminProductApiClient()


def get_billing_admin_product_api_client() -> BillingAdminProductApiClient:
    """Return the default billing admin product API layer instance."""

    return _billing_admin_product_api_client
