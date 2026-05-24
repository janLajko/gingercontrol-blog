"""Repository helpers for radar policy review."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from src.db.connection import acquire_connection, acquire_connection_with_transaction
from src.service.radar_policy_impact_service import (
    RadarPolicyImpact,
    build_radar_policy_impacts,
)


class RadarPolicyApiException(Exception):
    """API-facing exception for radar policy review operations."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def list_pending_radar_policy_updates(limit: int) -> list[dict[str, Any]]:
    """List policy updates waiting for human impact_json review."""

    with _acquire_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    source_key,
                    source_label,
                    source_url,
                    source_title,
                    headline,
                    published_at,
                    effective_date,
                    policy_extract_status,
                    policy_review_status,
                    action_calculate_status,
                    created_at,
                    updated_at,
                    jsonb_array_length(COALESCE(impact_json->'measures', '[]'::jsonb))
                        AS measures_count,
                    jsonb_array_length(COALESCE(impact_json->'scope_sets', '[]'::jsonb))
                        AS scope_sets_count,
                    jsonb_array_length(COALESCE(impact_json->'hts_modifications', '[]'::jsonb))
                        AS hts_modifications_count
                FROM radar_policy_updates
                WHERE policy_review_status = 'confirm_needed'
                    AND policy_extract_status = 'succeeded'
                    AND impact_json IS NOT NULL
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [_normalize_summary_row(row) for row in cur.fetchall()]


def get_radar_policy_update(policy_update_id: int) -> dict[str, Any]:
    """Return one radar policy update detail row."""

    with _acquire_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    source_key,
                    source_label,
                    source_url,
                    source_title,
                    source_metadata,
                    headline,
                    summary,
                    briefing,
                    published_at,
                    effective_date,
                    policy_extract_status,
                    policy_review_status,
                    action_calculate_status,
                    created_at,
                    updated_at,
                    impact_json,
                    jsonb_array_length(COALESCE(impact_json->'measures', '[]'::jsonb))
                        AS measures_count,
                    jsonb_array_length(COALESCE(impact_json->'scope_sets', '[]'::jsonb))
                        AS scope_sets_count,
                    jsonb_array_length(COALESCE(impact_json->'hts_modifications', '[]'::jsonb))
                        AS hts_modifications_count
                FROM radar_policy_updates
                WHERE id = %s
                """,
                (policy_update_id,),
            )
            row = cur.fetchone()
            if not row:
                raise RadarPolicyApiException(
                    404,
                    "not_found",
                    "Radar policy update not found.",
                )
            return _normalize_detail_row(row)


def preview_radar_policy_impacts(
    policy_update_id: int,
    impact_json: dict[str, Any],
) -> list[RadarPolicyImpact]:
    """Build impact rows without writing them."""

    policy = get_radar_policy_update(policy_update_id)
    return build_radar_policy_impacts(
        impact_json,
        policy_update_id=policy_update_id,
        policy_effective_date=policy["effective_date"],
        policy_published_at=policy["published_at"],
    )


def approve_radar_policy_update(
    policy_update_id: int,
    impact_json: dict[str, Any],
) -> tuple[dict[str, Any], list[RadarPolicyImpact]]:
    """Approve a policy update and write generated impact rows in one transaction."""

    with _acquire_connection_with_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    published_at,
                    effective_date,
                    policy_extract_status,
                    policy_review_status
                FROM radar_policy_updates
                WHERE id = %s
                FOR UPDATE
                """,
                (policy_update_id,),
            )
            row = cur.fetchone()
            if not row:
                raise RadarPolicyApiException(
                    404,
                    "not_found",
                    "Radar policy update not found.",
                )

            if (
                row["policy_review_status"] != "confirm_needed"
                or row["policy_extract_status"] != "succeeded"
            ):
                raise RadarPolicyApiException(
                    409,
                    "invalid_review_state",
                    "This radar policy update is no longer waiting for review.",
                )

            impacts = build_radar_policy_impacts(
                impact_json,
                policy_update_id=policy_update_id,
                policy_effective_date=_format_date(row["effective_date"]),
                policy_published_at=_format_datetime(row["published_at"]),
            )

            cur.execute(
                """
                UPDATE radar_policy_updates
                SET impact_json = %s,
                    policy_review_status = 'approved',
                    updated_at = now()
                WHERE id = %s
                """,
                (Jsonb(impact_json), policy_update_id),
            )
            cur.execute(
                "DELETE FROM radar_policy_impacts WHERE policy_update_id = %s",
                (policy_update_id,),
            )
            _insert_impacts(cur, policy_update_id, impacts)

    return get_radar_policy_update(policy_update_id), impacts


@contextmanager
def _acquire_connection() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    try:
        with acquire_connection() as conn:
            yield conn
    except RuntimeError as exc:
        raise RadarPolicyApiException(500, "database_pool_closed", str(exc)) from exc


@contextmanager
def _acquire_connection_with_transaction() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    try:
        with acquire_connection_with_transaction() as conn:
            yield conn
    except RuntimeError as exc:
        raise RadarPolicyApiException(500, "database_pool_closed", str(exc)) from exc


def _insert_impacts(
    cur: psycopg.Cursor[dict[str, Any]],
    policy_update_id: int,
    impacts: list[RadarPolicyImpact],
) -> None:
    if not impacts:
        return

    with cur.copy(
        """
        COPY radar_policy_impacts
            (policy_update_id, hts_number, impacted_type, effective_time, coos, row_desc)
        FROM STDIN
        """
    ) as copy:
        for impact in impacts:
            copy.write_row(
                (
                    policy_update_id,
                    impact["hts_number"],
                    impact["impacted_type"],
                    impact["effective_time"],
                    impact["coos"],
                    impact["row_desc"],
                )
            )


def _normalize_detail_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_summary_row(row)
    normalized.update(
        {
            "source_metadata": row.get("source_metadata") or {},
            "summary": row.get("summary") or "",
            "briefing": row.get("briefing") or "",
            "impact_json": row.get("impact_json"),
        }
    )
    return normalized


def _normalize_summary_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "source_key": row.get("source_key") or "",
        "source_label": row.get("source_label") or "",
        "source_url": row.get("source_url") or "",
        "source_title": row.get("source_title") or "",
        "headline": row.get("headline") or "",
        "published_at": _format_datetime(row.get("published_at")),
        "effective_date": _format_date(row.get("effective_date")),
        "policy_extract_status": row.get("policy_extract_status") or "",
        "policy_review_status": row.get("policy_review_status") or "",
        "action_calculate_status": row.get("action_calculate_status") or "",
        "created_at": _format_datetime(row.get("created_at")) or "",
        "updated_at": _format_datetime(row.get("updated_at")) or "",
        "measures_count": int(row.get("measures_count") or 0),
        "scope_sets_count": int(row.get("scope_sets_count") or 0),
        "hts_modifications_count": int(row.get("hts_modifications_count") or 0),
    }


def _format_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _format_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]
