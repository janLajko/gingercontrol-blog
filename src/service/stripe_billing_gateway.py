"""Stripe gateway for billing admin product synchronization."""

from __future__ import annotations

from typing import Any, Iterable
from urllib.parse import urlencode

import httpx

from src.config import settings


class StripeGatewayError(Exception):
    """Raised when Stripe returns an error response."""


class StripeBillingGateway:
    """Minimal Stripe HTTP gateway for Product and Price operations."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 20.0,
    ) -> None:
        self._api_key = api_key or settings.STRIPE_SECRET_KEY
        self._base_url = (base_url or settings.STRIPE_API_BASE_URL).rstrip("/")
        self._timeout = timeout

    async def create_product(
        self,
        *,
        name: str,
        description: str | None,
        active: bool,
        metadata: dict[str, str | None],
    ) -> dict[str, Any]:
        form_data = [
            ("name", name),
            ("active", _bool_to_str(active)),
            *_metadata_form_items(metadata),
        ]
        if description is not None:
            form_data.append(("description", description))
        return await self._request("POST", "/v1/products", data=form_data)

    async def update_product(
        self,
        product_id: str,
        *,
        name: str,
        description: str | None,
        active: bool,
        metadata: dict[str, str | None],
    ) -> dict[str, Any]:
        form_data = [
            ("name", name),
            ("description", description or ""),
            ("active", _bool_to_str(active)),
            *_metadata_form_items(metadata),
        ]
        return await self._request(
            "POST",
            f"/v1/products/{product_id}",
            data=form_data,
        )

    async def retrieve_product(self, product_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/products/{product_id}")

    async def create_price(
        self,
        *,
        product_id: str,
        active: bool,
        metadata: dict[str, str | None],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        form_data: list[tuple[str, str]] = [
            ("product", product_id),
            ("currency", str(payload["currency"])),
            ("unit_amount", str(payload["unit_amount"])),
            ("active", _bool_to_str(active)),
            *_metadata_form_items(metadata),
        ]

        billing_scheme = payload.get("billing_scheme")
        if billing_scheme:
            form_data.append(("billing_scheme", str(billing_scheme)))

        lookup_key = payload.get("lookup_key")
        if lookup_key:
            form_data.append(("lookup_key", str(lookup_key)))

        if payload["type"] == "recurring":
            form_data.extend(
                [
                    ("recurring[interval]", str(payload["recurring_interval"])),
                    (
                        "recurring[interval_count]",
                        str(payload["recurring_interval_count"]),
                    ),
                ]
            )

        return await self._request("POST", "/v1/prices", data=form_data)

    async def update_price(
        self,
        price_id: str,
        *,
        active: bool,
        metadata: dict[str, str | None],
    ) -> dict[str, Any]:
        form_data = [
            ("active", _bool_to_str(active)),
            *_metadata_form_items(metadata),
        ]
        return await self._request(
            "POST",
            f"/v1/prices/{price_id}",
            data=form_data,
        )

    async def retrieve_price(self, price_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/prices/{price_id}")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        data: Iterable[tuple[str, str]] | None = None,
    ) -> dict[str, Any]:
        if not self._api_key:
            raise StripeGatewayError("STRIPE_SECRET_KEY is not configured")

        try:
            request_headers = {
                "Authorization": f"Bearer {self._api_key}",
            }
            request_kwargs: dict[str, Any] = {}
            if data is not None:
                # Encode form data explicitly so AsyncClient does not treat the
                # tuple iterable as a sync request stream.
                request_headers["Content-Type"] = "application/x-www-form-urlencoded"
                request_kwargs["content"] = urlencode(list(data)).encode()

            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers=request_headers,
            ) as client:
                response = await client.request(method, path, **request_kwargs)
        except httpx.HTTPError as exc:
            raise StripeGatewayError(f"Stripe request failed: {exc}") from exc

        payload: dict[str, Any]
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.status_code >= 400:
            error_payload = payload.get("error")
            if isinstance(error_payload, dict):
                message = error_payload.get("message") or error_payload.get("type")
            else:
                message = None
            raise StripeGatewayError(message or f"Stripe returned HTTP {response.status_code}")

        return payload


def _metadata_form_items(
    metadata: dict[str, str | None],
) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for key, value in metadata.items():
        items.append((f"metadata[{key}]", "" if value is None else str(value)))
    return items


def _bool_to_str(value: bool) -> str:
    return "true" if value else "false"
