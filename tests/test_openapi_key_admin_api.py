"""OpenAPI key admin API tests with local SQLite persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config import settings
from src.db import base as db_base
from src.db.base import get_openapi_session_local
from src.db.models import OpenApiClientRecord, OpenApiKeyRecord
from src.db.service import init_db


@pytest.fixture
def openapi_key_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Generator[TestClient, None, None]:
    sqlite_path = tmp_path / "openapi-key-admin.sqlite3"
    database_url = f"sqlite:///{sqlite_path}"
    encryption_key = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("BILLING_DATABASE_URL", database_url)
    monkeypatch.setenv("OPENAPI_DATABASE", database_url)
    monkeypatch.setenv("OPENAPI_KEY_PEPPER", "test-pepper")
    monkeypatch.setenv("OPENAPI_KEY_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)
    monkeypatch.setattr(settings, "BILLING_DATABASE_URL", database_url)
    monkeypatch.setattr(settings, "OPENAPI_DATABASE", database_url)
    monkeypatch.setattr(settings, "OPENAPI_KEY_PEPPER", "test-pepper")
    monkeypatch.setattr(settings, "OPENAPI_KEY_ENCRYPTION_KEY", encryption_key)

    db_base._engine = None
    db_base._session_local = None
    db_base._billing_engine = None
    db_base._billing_session_local = None
    db_base._openapi_engine = None
    db_base._openapi_session_local = None
    init_db()

    session_local = get_openapi_session_local()
    assert session_local is not None
    session = session_local()
    try:
        session.add(
            OpenApiClientRecord(
                client_code="acme",
                name="ACME Trading",
                status="active",
            )
        )
        session.commit()
    finally:
        session.close()

    app = create_app()
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        db_base._engine = None
        db_base._session_local = None
        db_base._billing_engine = None
        db_base._billing_session_local = None
        db_base._openapi_engine = None
        db_base._openapi_session_local = None


def test_create_openapi_key_for_existing_client(openapi_key_client: TestClient) -> None:
    clients_response = openapi_key_client.get("/api/admin/billing/openapi-clients")
    assert clients_response.status_code == 200
    client_id = clients_response.json()["items"][0]["client_id"]

    create_response = openapi_key_client.post(
        "/api/admin/billing/openapi-keys",
        json={
            "client_id": client_id,
            "key_scope": "test",
            "rpm_limit": 600,
            "burst_limit": 150,
            "secret_version": "v1",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["api_key"].startswith("bb_test_")
    assert created["key_prefix"] == created["api_key"][:20]
    assert created["client_code"] == "acme"
    assert created["status"] == "active"

    keys_response = openapi_key_client.get("/api/admin/billing/openapi-keys")
    assert keys_response.status_code == 200
    keys = keys_response.json()["items"]
    assert keys[0]["key_prefix"] == created["key_prefix"]
    assert "api_key" not in keys[0]

    session_local = get_openapi_session_local()
    assert session_local is not None
    session = session_local()
    try:
        stored = session.get(OpenApiKeyRecord, created["key_id"])
        assert stored is not None
        assert stored.key_hash
        assert stored.encrypted_key_ciphertext
        assert stored.encrypted_key_algorithm == "AES-256-GCM"
    finally:
        session.close()


def test_delete_openapi_key_revokes_record(openapi_key_client: TestClient) -> None:
    clients_response = openapi_key_client.get("/api/admin/billing/openapi-clients")
    client_id = clients_response.json()["items"][0]["client_id"]

    create_response = openapi_key_client.post(
        "/api/admin/billing/openapi-keys",
        json={"client_id": client_id},
    )
    key_id = create_response.json()["key_id"]

    delete_response = openapi_key_client.delete(
        f"/api/admin/billing/openapi-keys/{key_id}"
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "revoked"

    keys_response = openapi_key_client.get(
        "/api/admin/billing/openapi-keys?status=revoked"
    )
    assert keys_response.status_code == 200
    assert keys_response.json()["items"][0]["key_id"] == key_id
