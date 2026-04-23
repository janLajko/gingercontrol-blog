"""Billing user admin API tests with local SQLite persistence."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config import settings
from src.db import base as db_base
from src.db.base import get_billing_session_local
from src.db.models import BillingFeaturePolicyRecord, BillingProductRecord, UserRecord
from src.db.service import init_db


@pytest.fixture
def user_billing_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Generator[TestClient, None, None]:
    sqlite_path = tmp_path / "billing-user-admin.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{sqlite_path}")
    monkeypatch.setenv("BILLING_DATABASE_URL", f"sqlite:///{sqlite_path}")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{sqlite_path}")
    monkeypatch.setattr(settings, "BILLING_DATABASE_URL", f"sqlite:///{sqlite_path}")

    db_base._engine = None
    db_base._session_local = None
    db_base._billing_engine = None
    db_base._billing_session_local = None
    init_db()
    _seed_user_billing_fixtures()

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


class TestBillingUserAdminRoutes:
    def test_search_users_by_email(self, user_billing_client: TestClient) -> None:
        response = user_billing_client.get(
            "/api/admin/billing/users/search",
            params={"keyword": "alice@example.com"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "items": [
                {
                    "user_id": 1,
                    "email": "alice@example.com",
                    "name": "Alice",
                    "company_name": "Acme Co",
                }
            ]
        }

    def test_create_and_cancel_manual_purchase(
        self,
        user_billing_client: TestClient,
    ) -> None:
        create_response = user_billing_client.post(
            "/api/admin/billing/users/1/manual-purchases",
            json={
                "product_code": "signup_trial_bundle",
                "purchase_starts_at": "2099-04-23T00:00:00Z",
                "purchase_ends_at": "2099-05-23T00:00:00Z",
                "reason": "contract bonus",
                "contract_no": "C-2026-001",
                "note": "first contract grant",
                "grants": [
                    {
                        "feature_key": "classification.hts.run",
                        "grant_mode": "prepaid_quota",
                        "quantity": 100,
                        "starts_at": "2099-04-23T00:00:00Z",
                        "ends_at": "2099-05-23T00:00:00Z",
                    },
                    {
                        "feature_key": "classification.api.access",
                        "grant_mode": "unlimited",
                        "starts_at": "2099-04-23T00:00:00Z",
                        "ends_at": "2099-05-23T00:00:00Z",
                    },
                ],
            },
        )

        assert create_response.status_code == 201
        created = create_response.json()
        assert created["product_code"] == "signup_trial_bundle"
        assert created["status"] == "pending"
        assert len(created["grants"]) == 2
        assert created["grants"][0]["status"] == "active"

        summary_response = user_billing_client.get(
            "/api/admin/billing/users/1/billing-summary"
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["user"]["email"] == "alice@example.com"
        assert len(summary["purchases"]) == 1
        assert summary["purchases"][0]["reason"] == "contract bonus"

        cancel_response = user_billing_client.post(
            f"/api/admin/billing/manual-purchases/{created['purchase_id']}/cancel",
            json={"reason": "contract revoked"},
        )
        assert cancel_response.status_code == 200
        canceled = cancel_response.json()
        assert canceled["status"] == "canceled"
        assert all(grant["status"] == "canceled" for grant in canceled["grants"])


def _seed_user_billing_fixtures() -> None:
    session_local = get_billing_session_local()
    assert session_local is not None
    session = session_local()
    try:
        now = datetime.utcnow()
        session.add(
            UserRecord(
                id=1,
                email="alice@example.com",
                name="Alice",
                company_name="Acme Co",
                created_at=now,
                updated_at=now,
            )
        )
        session.add_all(
            [
                BillingFeaturePolicyRecord(
                    feature_key="classification.hts.run",
                    control_mode="grant_required",
                    name="HTS Run",
                    description=None,
                    active=True,
                    config_json={},
                    created_at=now,
                    updated_at=now,
                ),
                BillingFeaturePolicyRecord(
                    feature_key="classification.api.access",
                    control_mode="grant_required",
                    name="API Access",
                    description=None,
                    active=True,
                    config_json={},
                    created_at=now,
                    updated_at=now,
                ),
                BillingProductRecord(
                    product_code="signup_trial_bundle",
                    product_family="system",
                    name="Signup Trial Bundle",
                    description="Admin manual grant template",
                    product_type="credit_pack",
                    stripe_product_id=None,
                    stripe_price_id=None,
                    active=True,
                    sort_order=0,
                    config_json=[
                        {
                            "feature_key": "classification.hts.run",
                            "grant_mode": "prepaid_quota",
                            "credits": 3,
                        }
                    ],
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()
