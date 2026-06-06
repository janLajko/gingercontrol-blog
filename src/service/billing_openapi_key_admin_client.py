"""Billing admin API layer for OpenAPI key management."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from src.config import settings
from src.db.base import get_openapi_session_local
from src.db.models import OpenApiClientRecord, OpenApiKeyRecord
from src.schemas.billing_admin import (
    OpenApiClient,
    OpenApiClientListResponse,
    OpenApiKey,
    OpenApiKeyCreateRequest,
    OpenApiKeyCreateResponse,
    OpenApiKeyListResponse,
)
from src.service.billing_admin_product_api_client import BillingAdminApiException
from src.service.openapi_key_crypto import (
    OpenApiKeyCryptoConfigError,
    encrypt_key_with_base64_key,
    hash_key_with_pepper,
)
from src.service.openapi_quota_defaults import (
    DEFAULT_ITEM_BURST_LIMIT,
    DEFAULT_ITEM_RPM_LIMIT,
)


DEFAULT_KEY_SCOPE = "test"
KEY_PREFIX_LENGTH = 20
MIN_API_KEY_LENGTH = KEY_PREFIX_LENGTH + 1
KEY_RANDOM_BYTES = 24
VALID_KEY_SCOPES = {"live", "test"}


class BillingOpenApiKeyAdminClient:
    """Backend API layer for CMS OpenAPI client/key operations."""

    def __init__(
        self,
        *,
        session_local_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._session_local_factory = session_local_factory or get_openapi_session_local

    async def list_clients(
        self,
        *,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> OpenApiClientListResponse:
        session = self._open_session()
        try:
            stmt = select(OpenApiClientRecord)
            count_stmt = select(func.count()).select_from(OpenApiClientRecord)

            normalized_status = (status or "").strip().lower()
            if normalized_status:
                stmt = stmt.where(OpenApiClientRecord.status == normalized_status)
                count_stmt = count_stmt.where(
                    OpenApiClientRecord.status == normalized_status
                )

            normalized_keyword = (keyword or "").strip()
            if normalized_keyword:
                pattern = f"%{normalized_keyword}%"
                predicate = or_(
                    OpenApiClientRecord.client_code.ilike(pattern),
                    OpenApiClientRecord.name.ilike(pattern),
                )
                stmt = stmt.where(predicate)
                count_stmt = count_stmt.where(predicate)

            stmt = stmt.order_by(
                OpenApiClientRecord.updated_at.desc(),
                OpenApiClientRecord.id.desc(),
            )
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)

            rows = session.execute(stmt).scalars().all()
            total = int(session.execute(count_stmt).scalar_one() or 0)
            return OpenApiClientListResponse(
                items=[_to_client_response(row) for row in rows],
                page=page,
                page_size=page_size,
                total=total,
            )
        finally:
            session.close()

    async def list_keys(
        self,
        *,
        client_id: int | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> OpenApiKeyListResponse:
        session = self._open_session()
        try:
            stmt = select(OpenApiKeyRecord, OpenApiClientRecord).join(
                OpenApiClientRecord,
                OpenApiClientRecord.id == OpenApiKeyRecord.client_id,
            )
            count_stmt = (
                select(func.count())
                .select_from(OpenApiKeyRecord)
                .join(
                    OpenApiClientRecord,
                    OpenApiClientRecord.id == OpenApiKeyRecord.client_id,
                )
            )

            if client_id is not None:
                stmt = stmt.where(OpenApiKeyRecord.client_id == client_id)
                count_stmt = count_stmt.where(OpenApiKeyRecord.client_id == client_id)

            normalized_status = (status or "").strip().lower()
            if normalized_status:
                stmt = stmt.where(OpenApiKeyRecord.status == normalized_status)
                count_stmt = count_stmt.where(
                    OpenApiKeyRecord.status == normalized_status
                )

            normalized_keyword = (keyword or "").strip()
            if normalized_keyword:
                pattern = f"%{normalized_keyword}%"
                predicate = or_(
                    OpenApiKeyRecord.key_prefix.ilike(pattern),
                    OpenApiClientRecord.client_code.ilike(pattern),
                    OpenApiClientRecord.name.ilike(pattern),
                )
                stmt = stmt.where(predicate)
                count_stmt = count_stmt.where(predicate)

            stmt = stmt.order_by(
                OpenApiKeyRecord.created_at.desc(),
                OpenApiKeyRecord.id.desc(),
            )
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)

            rows = session.execute(stmt).all()
            total = int(session.execute(count_stmt).scalar_one() or 0)
            return OpenApiKeyListResponse(
                items=[_to_key_response(key, client) for key, client in rows],
                page=page,
                page_size=page_size,
                total=total,
            )
        finally:
            session.close()

    async def create_key(
        self,
        payload: OpenApiKeyCreateRequest,
    ) -> OpenApiKeyCreateResponse:
        pepper = _require_configured_secret(
            name="OPENAPI_KEY_PEPPER",
            value=settings.OPENAPI_KEY_PEPPER,
        )
        encryption_key_base64 = _require_configured_secret(
            name="OPENAPI_KEY_ENCRYPTION_KEY",
            value=settings.OPENAPI_KEY_ENCRYPTION_KEY,
        )

        issued_key = (
            _require_non_empty_string(name="key", value=payload.key)
            if payload.key is not None
            else generate_api_key(key_scope=payload.key_scope)
        )
        key_prefix = build_key_prefix(issued_key)
        expires_at = _normalize_expires_at(payload.expires_at)

        try:
            key_hash = hash_key_with_pepper(raw_key=issued_key, pepper=pepper)
            encrypted = encrypt_key_with_base64_key(
                raw_key=issued_key,
                encryption_key_base64=encryption_key_base64,
                secret_version=payload.secret_version,
            )
        except (ValueError, OpenApiKeyCryptoConfigError) as exc:
            raise BillingAdminApiException(
                status_code=400,
                code="validation_error",
                message=str(exc),
            ) from exc

        session = self._open_session()
        try:
            client = session.execute(
                select(OpenApiClientRecord).where(
                    OpenApiClientRecord.id == payload.client_id
                )
            ).scalar_one_or_none()
            if client is None:
                raise BillingAdminApiException(
                    status_code=404,
                    code="openapi_client_not_found",
                    message=f"OpenAPI client not found: {payload.client_id}",
                    field_errors={"client_id": "not_found"},
                )

            now = datetime.now(timezone.utc)
            record = OpenApiKeyRecord(
                client_id=payload.client_id,
                key_prefix=key_prefix,
                key_hash=key_hash,
                encrypted_key_ciphertext=encrypted.ciphertext,
                encrypted_key_nonce=encrypted.nonce,
                encrypted_key_algorithm=encrypted.algorithm,
                secret_version=encrypted.secret_version,
                status="active",
                expires_at=expires_at,
                rpm_limit=payload.rpm_limit or DEFAULT_ITEM_RPM_LIMIT,
                burst_limit=payload.burst_limit or DEFAULT_ITEM_BURST_LIMIT,
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            session.commit()
            session.refresh(record)

            base = _to_key_response(record, client)
            return OpenApiKeyCreateResponse(
                **base.model_dump(),
                api_key=issued_key,
            )
        except IntegrityError as exc:
            session.rollback()
            raise BillingAdminApiException(
                status_code=409,
                code="openapi_key_conflict",
                message="The generated or provided OpenAPI key already exists.",
                field_errors={"key": "already_exists"},
            ) from exc
        except BillingAdminApiException:
            session.rollback()
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def revoke_key(self, key_id: int) -> OpenApiKey:
        session = self._open_session()
        try:
            record, client = _get_key_with_client_or_raise(session, key_id)
            if record.status != "revoked":
                record.status = "revoked"
                record.updated_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(record)
            return _to_key_response(record, client)
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
                message="OPENAPI_DATABASE is not configured",
            )
        return session_local()


def generate_api_key(*, key_scope: str = DEFAULT_KEY_SCOPE) -> str:
    scope = _require_non_empty_string(name="key_scope", value=key_scope).lower()
    if scope not in VALID_KEY_SCOPES:
        raise ValueError(
            f"key_scope must be one of: {', '.join(sorted(VALID_KEY_SCOPES))}."
        )
    random_part = secrets.token_urlsafe(KEY_RANDOM_BYTES).rstrip("=")
    return f"bb_{scope}_{random_part}"


def build_key_prefix(raw_key: str) -> str:
    normalized = _require_non_empty_string(name="raw_key", value=raw_key)
    if len(normalized) < MIN_API_KEY_LENGTH:
        raise ValueError(
            f"raw_key must be at least {MIN_API_KEY_LENGTH} characters long so "
            "key_prefix does not expose the full key."
        )
    return normalized[:KEY_PREFIX_LENGTH]


def _get_key_with_client_or_raise(
    session: Any,
    key_id: int,
) -> tuple[OpenApiKeyRecord, OpenApiClientRecord]:
    row = session.execute(
        select(OpenApiKeyRecord, OpenApiClientRecord)
        .join(
            OpenApiClientRecord,
            OpenApiClientRecord.id == OpenApiKeyRecord.client_id,
        )
        .where(OpenApiKeyRecord.id == key_id)
    ).one_or_none()
    if row is None:
        raise BillingAdminApiException(
            status_code=404,
            code="openapi_key_not_found",
            message=f"OpenAPI key not found: {key_id}",
        )
    return row


def _require_configured_secret(*, name: str, value: str | None) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise BillingAdminApiException(
            status_code=500,
            code="openapi_secret_not_configured",
            message=f"{name} is not configured on the backend service.",
        )
    return normalized


def _require_non_empty_string(*, name: str, value: str | None) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{name} is required.")
    return normalized


def _normalize_expires_at(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise BillingAdminApiException(
            status_code=400,
            code="validation_error",
            message="expires_at must include a timezone offset or use Z.",
            field_errors={"expires_at": "timezone_required"},
        )
    return value.astimezone(timezone.utc)


def _to_client_response(record: OpenApiClientRecord) -> OpenApiClient:
    return OpenApiClient(
        client_id=record.id,
        client_code=record.client_code,
        name=record.name,
        status=record.status,
        created_at=_to_rfc3339(record.created_at),
        updated_at=_to_rfc3339(record.updated_at),
    )


def _to_key_response(
    record: OpenApiKeyRecord,
    client: OpenApiClientRecord,
) -> OpenApiKey:
    return OpenApiKey(
        key_id=record.id,
        client_id=record.client_id,
        client_code=client.client_code,
        client_name=client.name,
        client_status=client.status,
        key_prefix=record.key_prefix,
        secret_version=record.secret_version,
        status=record.status,
        expires_at=_to_rfc3339(record.expires_at),
        rpm_limit=record.rpm_limit,
        burst_limit=record.burst_limit,
        created_at=_to_rfc3339(record.created_at),
        updated_at=_to_rfc3339(record.updated_at),
    )


def _to_rfc3339(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def get_billing_openapi_key_admin_client() -> BillingOpenApiKeyAdminClient:
    return BillingOpenApiKeyAdminClient()
