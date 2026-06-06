from __future__ import annotations

import argparse
import json
import secrets
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import psycopg
from psycopg.errors import ForeignKeyViolation, UniqueViolation


APP_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = APP_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from service.openapi_key_crypto import encrypt_key_with_base64_key, hash_key_with_pepper
from service.openapi_quota_defaults import (
    DEFAULT_ITEM_BURST_LIMIT,
    DEFAULT_ITEM_RPM_LIMIT,
)


DEFAULT_KEY_SCOPE = "test"
KEY_PREFIX_LENGTH = 20
MIN_API_KEY_LENGTH = KEY_PREFIX_LENGTH + 1
KEY_RANDOM_BYTES = 24
VALID_KEY_SCOPES = {"live", "test"}


@dataclass(frozen=True)
class IssuedOpenApiKey:
    key_id: int
    client_id: int
    client_code: str
    client_status: str
    key_prefix: str
    secret_version: str
    api_key: str
    rpm_limit: int
    burst_limit: int
    expires_at: str | None


def _require_non_empty_string(*, name: str, value: str | None) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{name} is required.")
    return normalized


def _require_positive_int(*, name: str, value: int) -> int:
    if int(value) <= 0:
        raise ValueError(f"{name} must be greater than 0.")
    return int(value)


def parse_expires_at(raw_value: str | None) -> datetime | None:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    return normalize_expires_at(value=parsed)


def normalize_expires_at(*, value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise ValueError("expires_at must include a timezone offset or use Z.")
    return value.astimezone(timezone.utc)


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


def insert_openapi_key(
    *,
    dsn: str,
    client_id: int,
    pepper: str,
    encryption_key_base64: str,
    raw_key: str | None = None,
    key_scope: str = DEFAULT_KEY_SCOPE,
    secret_version: str = "v1",
    rpm_limit: int = DEFAULT_ITEM_RPM_LIMIT,
    burst_limit: int = DEFAULT_ITEM_BURST_LIMIT,
    expires_at: datetime | None = None,
) -> IssuedOpenApiKey:
    normalized_dsn = _require_non_empty_string(name="dsn", value=dsn)
    normalized_client_id = _require_positive_int(name="client_id", value=client_id)
    normalized_expires_at = normalize_expires_at(value=expires_at)
    normalized_rpm_limit = _require_positive_int(name="rpm_limit", value=rpm_limit)
    normalized_burst_limit = _require_positive_int(
        name="burst_limit",
        value=burst_limit,
    )

    issued_key = (
        _require_non_empty_string(name="raw_key", value=raw_key)
        if raw_key is not None
        else generate_api_key(key_scope=key_scope)
    )
    key_prefix = build_key_prefix(issued_key)
    key_hash = hash_key_with_pepper(raw_key=issued_key, pepper=pepper)
    encrypted = encrypt_key_with_base64_key(
        raw_key=issued_key,
        encryption_key_base64=encryption_key_base64,
        secret_version=secret_version,
    )

    try:
        with psycopg.connect(normalized_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT client_code, status
                    FROM t_openapi_client
                    WHERE id = %s
                    """,
                    (normalized_client_id,),
                )
                client_row = cur.fetchone()
                if not client_row:
                    raise ValueError(
                        f"Client not found: client_id={normalized_client_id}."
                    )
                client_code, client_status = client_row

                cur.execute(
                    """
                    INSERT INTO t_openapi_key (
                        client_id,
                        key_prefix,
                        key_hash,
                        encrypted_key_ciphertext,
                        encrypted_key_nonce,
                        encrypted_key_algorithm,
                        secret_version,
                        status,
                        expires_at,
                        rpm_limit,
                        burst_limit
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        normalized_client_id,
                        key_prefix,
                        key_hash,
                        encrypted.ciphertext,
                        encrypted.nonce,
                        encrypted.algorithm,
                        encrypted.secret_version,
                        normalized_expires_at,
                        normalized_rpm_limit,
                        normalized_burst_limit,
                    ),
                )
                key_id = int(cur.fetchone()[0])
            conn.commit()
    except UniqueViolation as exc:
        raise RuntimeError(
            "Refusing to overwrite an existing OpenAPI key: the generated or provided "
            "key already exists in t_openapi_key."
        ) from exc
    except ForeignKeyViolation as exc:
        raise RuntimeError(
            f"Client not found or invalid foreign key: client_id={normalized_client_id}."
        ) from exc

    return IssuedOpenApiKey(
        key_id=key_id,
        client_id=normalized_client_id,
        client_code=str(client_code),
        client_status=str(client_status),
        key_prefix=key_prefix,
        secret_version=encrypted.secret_version,
        api_key=issued_key,
        rpm_limit=normalized_rpm_limit,
        burst_limit=normalized_burst_limit,
        expires_at=(
            normalized_expires_at.isoformat().replace("+00:00", "Z")
            if normalized_expires_at is not None
            else None
        ),
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Insert one OpenAPI key for an existing t_openapi_client record. "
            "This tool never reads .env or other environment variables."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dsn", required=True, help="Target PostgreSQL DSN.")
    parser.add_argument(
        "--client-id",
        required=True,
        type=int,
        help="Existing t_openapi_client.id.",
    )
    parser.add_argument(
        "--pepper",
        required=True,
        help="Plain OPENAPI_KEY_PEPPER value used for HMAC hashing.",
    )
    parser.add_argument(
        "--encryption-key-base64",
        required=True,
        help="Base64-encoded AES key string used for encrypted key storage.",
    )
    parser.add_argument(
        "--key",
        help=(
            "Explicit API key to insert. If omitted, a high-entropy key is generated "
            "and printed as the final issuer-facing value."
        ),
    )
    parser.add_argument(
        "--key-scope",
        choices=sorted(VALID_KEY_SCOPES),
        default=DEFAULT_KEY_SCOPE,
        help="Key prefix scope used when --key is omitted. Default: test.",
    )
    parser.add_argument(
        "--secret-version",
        default="v1",
        help=(
            "Metadata version for the secret pair used to issue the key. "
            "This version covers both OPENAPI_KEY_PEPPER and OPENAPI_KEY_ENCRYPTION_KEY."
        ),
    )
    parser.add_argument(
        "--rpm-limit",
        type=int,
        default=DEFAULT_ITEM_RPM_LIMIT,
        help=f"Per-key item quota per minute. Default: {DEFAULT_ITEM_RPM_LIMIT}.",
    )
    parser.add_argument(
        "--burst-limit",
        type=int,
        default=DEFAULT_ITEM_BURST_LIMIT,
        help=f"Per-key item burst quota. Default: {DEFAULT_ITEM_BURST_LIMIT}.",
    )
    parser.add_argument(
        "--expires-at",
        help="Optional RFC3339 timestamp, for example 2026-04-03T12:00:00Z.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        issued = insert_openapi_key(
            dsn=args.dsn,
            client_id=args.client_id,
            pepper=args.pepper,
            encryption_key_base64=args.encryption_key_base64,
            raw_key=args.key,
            key_scope=args.key_scope,
            secret_version=args.secret_version,
            rpm_limit=args.rpm_limit,
            burst_limit=args.burst_limit,
            expires_at=parse_expires_at(args.expires_at),
        )
    except (ValueError, RuntimeError, psycopg.Error) as exc:
        parser.exit(1, f"error: {exc}\n")
    print(json.dumps(asdict(issued), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
