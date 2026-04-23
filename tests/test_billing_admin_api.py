"""Billing admin API tests with local SQLite persistence and fake Stripe."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config import settings
from src.db import base as db_base
from src.db.service import init_db
from src.service.billing_admin_product_api_client import (
    BillingAdminProductApiClient,
    get_billing_admin_product_api_client,
)


class FakeStripeGateway:
    """In-memory Stripe gateway used by API tests."""

    def __init__(self) -> None:
        self.products: dict[str, dict[str, Any]] = {}
        self.prices: dict[str, dict[str, Any]] = {}
        self._product_seq = 0
        self._price_seq = 0

    async def create_product(
        self,
        *,
        name: str,
        description: str | None,
        active: bool,
        metadata: dict[str, str | None],
    ) -> dict[str, Any]:
        self._product_seq += 1
        product_id = f"prod_{self._product_seq}"
        product = {
            "id": product_id,
            "name": name,
            "description": description,
            "active": active,
            "metadata": _compact_metadata(metadata),
        }
        self.products[product_id] = product
        return dict(product)

    async def update_product(
        self,
        product_id: str,
        *,
        name: str,
        description: str | None,
        active: bool,
        metadata: dict[str, str | None],
    ) -> dict[str, Any]:
        product = self.products[product_id]
        product.update(
            {
                "name": name,
                "description": description,
                "active": active,
                "metadata": _compact_metadata(metadata),
            }
        )
        return dict(product)

    async def retrieve_product(self, product_id: str) -> dict[str, Any]:
        return dict(self.products[product_id])

    async def create_price(
        self,
        *,
        product_id: str,
        active: bool,
        metadata: dict[str, str | None],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._price_seq += 1
        price_id = f"price_{self._price_seq}"
        price = {
            "id": price_id,
            "product": product_id,
            "currency": payload["currency"],
            "unit_amount": payload["unit_amount"],
            "billing_scheme": payload.get("billing_scheme") or "",
            "lookup_key": payload.get("lookup_key"),
            "type": payload["type"],
            "recurring": (
                {
                    "interval": payload["recurring_interval"],
                    "interval_count": payload["recurring_interval_count"],
                }
                if payload["type"] == "recurring"
                else None
            ),
            "active": active,
            "metadata": _compact_metadata(metadata),
        }
        self.prices[price_id] = price
        return dict(price)

    async def update_price(
        self,
        price_id: str,
        *,
        active: bool,
        metadata: dict[str, str | None],
    ) -> dict[str, Any]:
        price = self.prices[price_id]
        price["active"] = active
        if metadata:
            existing_metadata = dict(price.get("metadata") or {})
            for key, value in metadata.items():
                if value is None:
                    existing_metadata.pop(key, None)
                else:
                    existing_metadata[key] = value
            price["metadata"] = existing_metadata
        return dict(price)

    async def retrieve_price(self, price_id: str) -> dict[str, Any]:
        return dict(self.prices[price_id])


@pytest.fixture
def billing_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Generator[tuple[TestClient, FakeStripeGateway], None, None]:
    sqlite_path = tmp_path / "billing-admin.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{sqlite_path}")
    monkeypatch.setenv("BILLING_DATABASE_URL", f"sqlite:///{sqlite_path}")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{sqlite_path}")
    monkeypatch.setattr(settings, "BILLING_DATABASE_URL", f"sqlite:///{sqlite_path}")

    db_base._engine = None
    db_base._session_local = None
    db_base._billing_engine = None
    db_base._billing_session_local = None
    init_db()

    fake_stripe = FakeStripeGateway()
    api_client = BillingAdminProductApiClient(
        stripe_gateway=fake_stripe,
    )

    app = create_app()
    app.dependency_overrides[get_billing_admin_product_api_client] = lambda: api_client

    client = TestClient(app)
    try:
        yield client, fake_stripe
    finally:
        client.close()
        app.dependency_overrides.clear()
        db_base._engine = None
        db_base._session_local = None
        db_base._billing_engine = None
        db_base._billing_session_local = None


class TestBillingAdminRoutes:
    def test_create_and_get_product_detail(
        self,
        billing_client: tuple[TestClient, FakeStripeGateway],
    ) -> None:
        client, fake_stripe = billing_client

        create_response = client.post(
            "/api/admin/billing/products",
            json={
                "product_code": "classification_pack_500",
                "product_family": "classification",
                "name": "Classification Pack 500",
                "description": "classification credits pack: 500",
                "product_type": "credit_pack",
                "active": True,
                "sort_order": 25,
                "config_json": {
                    "feature_key": "classification.run",
                    "grant_mode": "prepaid_quota",
                    "credits": 500,
                },
                "stripe_sync": {
                    "mode": "create",
                    "product_name": "Classification Pack 500",
                    "price": {
                        "currency": "usd",
                        "unit_amount": 9900,
                        "billing_scheme": "per_unit",
                        "type": "one_time",
                    },
                },
            },
        )

        assert create_response.status_code == 201
        created = create_response.json()
        assert created["product_code"] == "classification_pack_500"
        assert created["stripe_product_id"] == "prod_1"
        assert created["stripe_price_id"] == "price_1"
        assert fake_stripe.products["prod_1"]["metadata"]["product_family"] == "classification"

        detail_response = client.get(
            "/api/admin/billing/products/classification_pack_500"
        )

        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["stripe_catalog"]["unit_amount"] == 9900
        assert detail["grant_preview"] == [
            {
                "feature_key": "classification.run",
                "grant_mode": "prepaid_quota",
                "granted_quantity": 500,
            }
        ]

    def test_create_product_with_multiple_config_json_entries(
        self,
        billing_client: tuple[TestClient, FakeStripeGateway],
    ) -> None:
        client, _ = billing_client

        create_response = client.post(
            "/api/admin/billing/products",
            json={
                "product_code": "bundle_monthly",
                "product_family": "simulate",
                "name": "Bundle Monthly",
                "description": "simulate + classification bundle",
                "product_type": "subscription",
                "active": True,
                "sort_order": 5,
                "config_json": [
                    {
                        "feature_key": "simulate.run",
                        "grant_mode": "unlimited",
                    },
                    {
                        "feature_key": "classification.run",
                        "grant_mode": "prepaid_quota",
                        "credits": 100,
                    },
                ],
                "stripe_sync": {
                    "mode": "create",
                    "product_name": "Bundle Monthly",
                    "price": {
                        "currency": "usd",
                        "unit_amount": 2900,
                        "type": "recurring",
                        "recurring_interval": "month",
                        "recurring_interval_count": 1,
                    },
                },
            },
        )

        assert create_response.status_code == 201
        created = create_response.json()
        assert created["config_json"] == [
            {
                "feature_key": "simulate.run",
                "grant_mode": "unlimited",
            },
            {
                "feature_key": "classification.run",
                "grant_mode": "prepaid_quota",
                "credits": 100,
            },
        ]

        detail_response = client.get("/api/admin/billing/products/bundle_monthly")

        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["grant_preview"] == [
            {
                "feature_key": "simulate.run",
                "grant_mode": "unlimited",
                "granted_quantity": None,
            },
            {
                "feature_key": "classification.run",
                "grant_mode": "prepaid_quota",
                "granted_quantity": 100,
            },
        ]

    def test_replace_product_with_price_change_creates_new_price(
        self,
        billing_client: tuple[TestClient, FakeStripeGateway],
    ) -> None:
        client, fake_stripe = billing_client
        self._create_credit_pack(client)

        replace_response = client.put(
            "/api/admin/billing/products/classification_pack_100",
            json={
                "name": "Classification Pack 100",
                "description": "classification credits pack: 100",
                "active": True,
                "sort_order": 20,
                "config_json": {
                    "feature_key": "classification.run",
                    "grant_mode": "prepaid_quota",
                    "credits": 100,
                },
                "stripe_sync": {
                    "update_product": True,
                    "price_change": {
                        "enabled": True,
                        "currency": "usd",
                        "unit_amount": 12900,
                        "billing_scheme": "per_unit",
                        "type": "one_time",
                    },
                },
            },
        )

        assert replace_response.status_code == 200
        payload = replace_response.json()
        assert payload["stripe_price_id"] == "price_2"
        assert fake_stripe.prices["price_1"]["active"] is False
        assert fake_stripe.prices["price_2"]["unit_amount"] == 12900

    def test_patch_active_syncs_local_and_stripe_state(
        self,
        billing_client: tuple[TestClient, FakeStripeGateway],
    ) -> None:
        client, fake_stripe = billing_client
        self._create_credit_pack(client)

        patch_response = client.patch(
            "/api/admin/billing/products/classification_pack_100",
            json={"active": False},
        )

        assert patch_response.status_code == 200
        payload = patch_response.json()
        assert payload["active"] is False
        assert fake_stripe.products["prod_1"]["active"] is False
        assert fake_stripe.prices["price_1"]["active"] is False

    def test_manual_sync_replays_local_metadata_to_stripe(
        self,
        billing_client: tuple[TestClient, FakeStripeGateway],
    ) -> None:
        client, fake_stripe = billing_client
        self._create_credit_pack(client)

        fake_stripe.products["prod_1"]["metadata"] = {}
        fake_stripe.prices["price_1"]["metadata"] = {}

        sync_response = client.post(
            "/api/admin/billing/products/classification_pack_100/sync-stripe",
            json={"sync_product": True, "sync_price": True},
        )

        assert sync_response.status_code == 200
        assert sync_response.json() == {
            "ok": True,
            "product_code": "classification_pack_100",
            "stripe_product_id": "prod_1",
            "stripe_price_id": "price_1",
        }
        assert fake_stripe.products["prod_1"]["metadata"]["product_code"] == "classification_pack_100"
        assert fake_stripe.prices["price_1"]["metadata"]["feature_key"] == "classification.run"

    def test_bind_existing_validates_price_type(
        self,
        billing_client: tuple[TestClient, FakeStripeGateway],
    ) -> None:
        client, fake_stripe = billing_client

        fake_stripe.products["prod_bound"] = {
            "id": "prod_bound",
            "name": "Bound Product",
            "description": None,
            "active": True,
            "metadata": {},
        }
        fake_stripe.prices["price_bound"] = {
            "id": "price_bound",
            "product": "prod_bound",
            "currency": "usd",
            "unit_amount": 9900,
            "billing_scheme": "per_unit",
            "lookup_key": None,
            "type": "one_time",
            "recurring": None,
            "active": True,
            "metadata": {},
        }

        response = client.post(
            "/api/admin/billing/products",
            json={
                "product_code": "simulate_monthly",
                "product_family": "simulate",
                "name": "Simulate Monthly",
                "description": "simulate monthly unlimited access",
                "product_type": "subscription",
                "active": True,
                "sort_order": 10,
                "config_json": {
                    "feature_key": "simulate.run",
                    "grant_mode": "unlimited",
                },
                "stripe_sync": {
                    "mode": "bind_existing",
                    "stripe_product_id": "prod_bound",
                    "stripe_price_id": "price_bound",
                },
            },
        )

        assert response.status_code == 422
        assert response.json() == {
            "detail": {
                "code": "stripe_binding_invalid",
                "message": "Stripe Price type does not match local product_type",
                "field_errors": {
                    "stripe_sync.stripe_price_id": "type_mismatch",
                },
            }
        }

    def test_create_system_product_without_stripe_sync(
        self,
        billing_client: tuple[TestClient, FakeStripeGateway],
    ) -> None:
        client, fake_stripe = billing_client

        response = client.post(
            "/api/admin/billing/products",
            json={
                "product_code": "signup_trial_bundle",
                "product_family": "system",
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["product_code"] == "signup_trial_bundle"
        assert payload["name"] == "signup_trial_bundle"
        assert payload["product_type"] == "credit_pack"
        assert payload["stripe_product_id"] == ""
        assert payload["stripe_price_id"] == ""
        assert payload["config_json"] == []
        assert fake_stripe.products == {}
        assert fake_stripe.prices == {}

        detail_response = client.get("/api/admin/billing/products/signup_trial_bundle")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["stripe_catalog"] is None
        assert detail["grant_preview"] == []

    @staticmethod
    def _create_credit_pack(client: TestClient) -> None:
        response = client.post(
            "/api/admin/billing/products",
            json={
                "product_code": "classification_pack_100",
                "product_family": "classification",
                "name": "Classification Pack 100",
                "description": "classification credits pack: 100",
                "product_type": "credit_pack",
                "active": True,
                "sort_order": 20,
                "config_json": {
                    "feature_key": "classification.run",
                    "grant_mode": "prepaid_quota",
                    "credits": 100,
                },
                "stripe_sync": {
                    "mode": "create",
                    "product_name": "Classification Pack 100",
                    "price": {
                        "currency": "usd",
                        "unit_amount": 9900,
                        "billing_scheme": "per_unit",
                        "type": "one_time",
                    },
                },
            },
        )

        assert response.status_code == 201


def _compact_metadata(metadata: dict[str, str | None]) -> dict[str, str]:
    return {
        key: value
        for key, value in metadata.items()
        if value is not None
    }
