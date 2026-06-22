"""Repository helpers for user management admin APIs."""

from __future__ import annotations

from typing import Any

import psycopg

from src.db.user_manage_connection import (
    acquire_connection,
    acquire_connection_with_transaction,
)
from src.schemas.user_manage import EMAIL_DOMAIN, ManagedUserCreateRequest


DEFAULT_USER_PASSWORD = "123456"


class UserManageApiException(Exception):
    """API-facing exception for user management operations."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


USER_COLUMNS = """
    id,
    email,
    name,
    avatar_url,
    provider,
    provider_sub,
    company_name,
    job_title,
    profile_completed,
    email_verified,
    last_login_at,
    created_at,
    updated_at,
    source,
    callsign,
    language,
    password,
    is_deleted
"""


def list_users(
    *,
    keyword: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Return a paginated active user list."""

    where_sql, params = _build_user_filters(keyword=keyword)
    offset = (page - 1) * page_size

    with _acquire_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT count(*) AS total
                FROM users
                {where_sql}
                """,
                params,
            )
            total = int(cur.fetchone()["total"])

            cur.execute(
                f"""
                SELECT {USER_COLUMNS}
                FROM users
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


def get_user(user_id: int) -> dict[str, Any]:
    """Return one active user row."""

    with _acquire_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {USER_COLUMNS}
                FROM users
                WHERE id = %s
                    AND is_deleted = false
                """,
                (user_id,),
            )
            row = cur.fetchone()

    if not row:
        raise UserManageApiException(404, "not_found", "User not found.")

    return row


def create_user(payload: ManagedUserCreateRequest) -> dict[str, Any]:
    """Create one manual user."""

    email = f"{payload.email_prefix}{EMAIL_DOMAIN}"
    provider_sub = f"manual:{email}"

    try:
        with _acquire_connection_with_transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (
                        email,
                        name,
                        provider,
                        provider_sub,
                        company_name,
                        job_title,
                        profile_completed,
                        email_verified,
                        source,
                        callsign,
                        language,
                        password
                    )
                    VALUES (
                        %s,
                        %s,
                        'manual',
                        %s,
                        %s,
                        %s,
                        true,
                        true,
                        'manual',
                        %s,
                        %s,
                        %s
                    )
                    RETURNING id
                    """,
                    (
                        email,
                        _blank_to_none(payload.name),
                        provider_sub,
                        _blank_to_none(payload.company_name),
                        _blank_to_none(payload.job_title),
                        _blank_to_none(payload.callsign),
                        _blank_to_none(payload.language),
                        DEFAULT_USER_PASSWORD,
                    ),
                )
                user_id = int(cur.fetchone()["id"])
    except psycopg.errors.UniqueViolation as exc:
        raise UserManageApiException(
            409,
            "duplicate_user",
            "A user with this email already exists.",
        ) from exc

    return get_user(user_id)


def delete_user(user_id: int) -> None:
    """Soft-delete one user by setting is_deleted."""

    with _acquire_connection_with_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET is_deleted = true,
                    updated_at = now()
                WHERE id = %s
                    AND is_deleted = false
                RETURNING id
                """,
                (user_id,),
            )
            row = cur.fetchone()

    if not row:
        raise UserManageApiException(404, "not_found", "User not found.")


def _build_user_filters(*, keyword: str | None) -> tuple[str, tuple[Any, ...]]:
    filters = ["is_deleted = false"]
    params: list[Any] = []

    if keyword:
        like_value = f"%{keyword.strip()}%"
        filters.append(
            """
            (
                email ILIKE %s
                OR name ILIKE %s
                OR company_name ILIKE %s
                OR callsign ILIKE %s
            )
            """
        )
        params.extend([like_value, like_value, like_value, like_value])

    return f"WHERE {' AND '.join(filters)}", tuple(params)


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _acquire_connection():
    return acquire_connection()


def _acquire_connection_with_transaction():
    return acquire_connection_with_transaction()
