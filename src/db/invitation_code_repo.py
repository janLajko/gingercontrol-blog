"""Repository helpers for invitation code admin APIs."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from secrets import choice
from typing import Any

import psycopg

from src.db.invitation_code_connection import (
    acquire_connection,
    acquire_connection_with_transaction,
)
from src.schemas.invitation_code import (
    InvitationCodeCreateRequest,
    InvitationCodePatchRequest,
    InvitationCodeStatus,
    InvitationCodeType,
)


CODE_CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class InvitationCodeApiException(Exception):
    """API-facing exception for invitation code admin operations."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def list_invitation_codes(
    *,
    code_type: InvitationCodeType | None,
    status: InvitationCodeStatus | None,
    keyword: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Return a paginated invitation code list."""

    where_sql, params = _build_code_filters(
        code_type=code_type,
        status=status,
        keyword=keyword,
    )
    offset = (page - 1) * page_size

    with _acquire_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT count(*) AS total
                FROM invitation_codes
                {where_sql}
                """,
                params,
            )
            total = int(cur.fetchone()["total"])

            cur.execute(
                f"""
                SELECT
                    id,
                    code,
                    code_type,
                    prefix,
                    code_length,
                    max_uses,
                    used_count,
                    valid_from,
                    valid_until,
                    status,
                    note,
                    created_by,
                    created_at,
                    updated_at,
                    disabled_at
                FROM invitation_codes
                {where_sql}
                ORDER BY created_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                (*params, page_size, offset),
            )

            return {
                "items": cur.fetchall(),
                "page": page,
                "page_size": page_size,
                "total": total,
            }


def get_invitation_code(invitation_code_id: int) -> dict[str, Any]:
    """Return one invitation code row."""

    with _acquire_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    code,
                    code_type,
                    prefix,
                    code_length,
                    max_uses,
                    used_count,
                    valid_from,
                    valid_until,
                    status,
                    note,
                    created_by,
                    created_at,
                    updated_at,
                    disabled_at
                FROM invitation_codes
                WHERE id = %s
                """,
                (invitation_code_id,),
            )
            row = cur.fetchone()

    if not row:
        raise InvitationCodeApiException(
            404,
            "not_found",
            "Invitation code not found.",
        )

    return row


def create_invitation_code(payload: InvitationCodeCreateRequest) -> dict[str, Any]:
    """Create one invitation code."""

    code = payload.code

    with _acquire_connection_with_transaction() as conn:
        with conn.cursor() as cur:
            if code:
                _ensure_code_available(cur, code)
            else:
                code = _generate_available_code(cur, payload.prefix, payload.code_length)

            assert code is not None
            cur.execute(
                """
                INSERT INTO invitation_codes (
                    code,
                    code_type,
                    prefix,
                    code_length,
                    max_uses,
                    valid_from,
                    valid_until,
                    status,
                    note,
                    created_by,
                    disabled_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    CASE WHEN %s = 'disabled' THEN now() ELSE NULL END
                )
                RETURNING id
                """,
                (
                    code,
                    payload.code_type,
                    payload.prefix,
                    payload.code_length,
                    payload.max_uses,
                    payload.valid_from,
                    payload.valid_until,
                    payload.status,
                    payload.note,
                    payload.created_by,
                    payload.status,
                ),
            )
            invitation_code_id = int(cur.fetchone()["id"])

    return get_invitation_code(invitation_code_id)


def patch_invitation_code(
    invitation_code_id: int,
    payload: InvitationCodePatchRequest,
) -> dict[str, Any]:
    """Patch mutable invitation code fields."""

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return get_invitation_code(invitation_code_id)

    with _acquire_connection_with_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, code, used_count, max_uses, valid_from, valid_until
                FROM invitation_codes
                WHERE id = %s
                FOR UPDATE
                """,
                (invitation_code_id,),
            )
            existing = cur.fetchone()
            if not existing:
                raise InvitationCodeApiException(
                    404,
                    "not_found",
                    "Invitation code not found.",
                )

            _validate_patch_against_existing(existing, updates)

            set_parts: list[str] = []
            params: list[Any] = []
            for field in (
                "code_type",
                "prefix",
                "code_length",
                "max_uses",
                "valid_from",
                "valid_until",
                "status",
                "note",
            ):
                if field in updates:
                    set_parts.append(f"{field} = %s")
                    params.append(updates[field])

            if "status" in updates:
                set_parts.append(
                    "disabled_at = CASE WHEN %s = 'disabled' THEN COALESCE(disabled_at, now()) ELSE NULL END"
                )
                params.append(updates["status"])

            set_parts.append("updated_at = now()")

            cur.execute(
                f"""
                UPDATE invitation_codes
                SET {", ".join(set_parts)}
                WHERE id = %s
                """,
                (*params, invitation_code_id),
            )

    return get_invitation_code(invitation_code_id)


def delete_invitation_code(invitation_code_id: int) -> None:
    """Delete one invitation code and its usage records through FK cascade."""

    with _acquire_connection_with_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM invitation_codes
                WHERE id = %s
                RETURNING id
                """,
                (invitation_code_id,),
            )
            row = cur.fetchone()

    if not row:
        raise InvitationCodeApiException(
            404,
            "not_found",
            "Invitation code not found.",
        )


def list_invitation_code_usages(
    *,
    invitation_code_id: int,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Return usage records for one invitation code."""

    code = get_invitation_code(invitation_code_id)["code"]
    offset = (page - 1) * page_size

    with _acquire_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) AS total
                FROM invitation_code_usages
                WHERE code = %s
                """,
                (code,),
            )
            total = int(cur.fetchone()["total"])

            cur.execute(
                """
                SELECT id, code, user_id, used_at
                FROM invitation_code_usages
                WHERE code = %s
                ORDER BY used_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                (code, page_size, offset),
            )
            return {
                "items": cur.fetchall(),
                "page": page,
                "page_size": page_size,
                "total": total,
            }


def _build_code_filters(
    *,
    code_type: InvitationCodeType | None,
    status: InvitationCodeStatus | None,
    keyword: str | None,
) -> tuple[str, tuple[Any, ...]]:
    clauses: list[str] = []
    params: list[Any] = []

    if code_type:
        clauses.append("code_type = %s")
        params.append(code_type)

    if status:
        clauses.append("status = %s")
        params.append(status)

    if keyword and keyword.strip():
        clauses.append("(code ILIKE %s OR note ILIKE %s OR created_by ILIKE %s)")
        pattern = f"%{keyword.strip()}%"
        params.extend([pattern, pattern, pattern])

    if not clauses:
        return "", tuple()

    return "WHERE " + " AND ".join(clauses), tuple(params)


def _generate_code(prefix: str, code_length: int) -> str:
    body_length = code_length - len(prefix)
    return prefix + "".join(choice(CODE_CHARSET) for _ in range(body_length))


def _generate_available_code(
    cur: psycopg.Cursor[dict[str, Any]],
    prefix: str,
    code_length: int,
) -> str:
    for _ in range(10):
        code = _generate_code(prefix, code_length)
        cur.execute("SELECT id FROM invitation_codes WHERE code = %s", (code,))
        if not cur.fetchone():
            return code

    raise InvitationCodeApiException(
        409,
        "code_generation_failed",
        "Failed to generate a unique invitation code.",
    )


def _ensure_code_available(
    cur: psycopg.Cursor[dict[str, Any]],
    code: str,
) -> None:
    cur.execute("SELECT id FROM invitation_codes WHERE code = %s", (code,))
    if cur.fetchone():
        raise InvitationCodeApiException(
            409,
            "duplicate_code",
            "Invitation code already exists.",
        )


def _validate_patch_against_existing(
    existing: dict[str, Any],
    updates: dict[str, Any],
) -> None:
    code = existing["code"]
    next_prefix = updates.get("prefix", "")
    if "prefix" not in updates:
        next_prefix = None

    if next_prefix is not None and next_prefix and not code.startswith(next_prefix):
        raise InvitationCodeApiException(
            422,
            "invalid_prefix",
            "prefix must match the existing code.",
        )

    next_code_length = updates.get("code_length")
    if next_code_length is not None and len(code) != next_code_length:
        raise InvitationCodeApiException(
            422,
            "invalid_code_length",
            "code_length must equal the existing code length.",
        )

    next_max_uses = updates.get("max_uses")
    if next_max_uses is not None and existing["used_count"] > next_max_uses:
        raise InvitationCodeApiException(
            422,
            "invalid_max_uses",
            "max_uses cannot be lower than used_count.",
        )

    next_valid_from = updates.get("valid_from", existing["valid_from"])
    next_valid_until = updates.get("valid_until", existing["valid_until"])
    if next_valid_from and next_valid_until and next_valid_from >= next_valid_until:
        raise InvitationCodeApiException(
            422,
            "invalid_valid_range",
            "valid_from must be before valid_until.",
        )


@contextmanager
def _acquire_connection() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    try:
        with acquire_connection() as conn:
            yield conn
    except RuntimeError as exc:
        raise InvitationCodeApiException(500, "database_pool_closed", str(exc)) from exc


@contextmanager
def _acquire_connection_with_transaction() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    try:
        with acquire_connection_with_transaction() as conn:
            yield conn
    except RuntimeError as exc:
        raise InvitationCodeApiException(500, "database_pool_closed", str(exc)) from exc
