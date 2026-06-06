from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


_DEFAULT_SECRET_VERSION = "v1"


class OpenApiKeyCryptoConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class EncryptedKeyMaterial:
    ciphertext: str
    nonce: str
    algorithm: str
    secret_version: str


def _require_non_empty_string(*, name: str, value: str | None) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{name} is required.")
    return normalized


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise OpenApiKeyCryptoConfigError(f"{name} is required.")
    return value


def decode_encryption_key(*, encryption_key_base64: str) -> bytes:
    encoded = _require_non_empty_string(
        name="encryption_key_base64",
        value=encryption_key_base64,
    )
    try:
        key = base64.b64decode(encoded, altchars=b"-_", validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise OpenApiKeyCryptoConfigError(
            "encryption_key_base64 must be a valid base64-encoded string."
        ) from exc
    if len(key) not in (16, 24, 32):
        raise OpenApiKeyCryptoConfigError(
            "encryption_key_base64 must decode to 16, 24, or 32 bytes."
        )
    return key


def hash_key_with_pepper(*, raw_key: str, pepper: str) -> str:
    key = _require_non_empty_string(name="raw_key", value=raw_key)
    normalized_pepper = _require_non_empty_string(name="pepper", value=pepper)
    return hmac.new(
        normalized_pepper.encode("utf-8"),
        key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def encrypt_key_with_base64_key(
    *,
    raw_key: str,
    encryption_key_base64: str,
    secret_version: str = _DEFAULT_SECRET_VERSION,
) -> EncryptedKeyMaterial:
    key = _require_non_empty_string(name="raw_key", value=raw_key)
    normalized_secret_version = _require_non_empty_string(
        name="secret_version",
        value=secret_version,
    )
    cipher_key = decode_encryption_key(encryption_key_base64=encryption_key_base64)
    cipher = AESGCM(cipher_key)
    nonce = os.urandom(12)
    ciphertext = cipher.encrypt(
        nonce,
        key.encode("utf-8"),
        f"openapi-key:{normalized_secret_version}".encode("utf-8"),
    )
    key_bits = len(cipher_key) * 8
    return EncryptedKeyMaterial(
        ciphertext=base64.urlsafe_b64encode(ciphertext).decode("ascii"),
        nonce=base64.urlsafe_b64encode(nonce).decode("ascii"),
        algorithm=f"AES-{key_bits}-GCM",
        secret_version=normalized_secret_version,
    )


class OpenApiKeyCrypto:
    def hash_key(self, *, raw_key: str, pepper: str | None = None) -> str:
        return hash_key_with_pepper(
            raw_key=raw_key,
            pepper=pepper if pepper is not None else _require_env("OPENAPI_KEY_PEPPER"),
        )

    def encrypt_key(
        self,
        *,
        raw_key: str,
        encryption_key_base64: str | None = None,
        secret_version: str = _DEFAULT_SECRET_VERSION,
    ) -> EncryptedKeyMaterial:
        return encrypt_key_with_base64_key(
            raw_key=raw_key,
            encryption_key_base64=(
                encryption_key_base64
                if encryption_key_base64 is not None
                else _require_env("OPENAPI_KEY_ENCRYPTION_KEY")
            ),
            secret_version=secret_version,
        )


openapi_key_crypto = OpenApiKeyCrypto()
