"""Billing admin manual user billing routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.schemas.billing_admin import (
    BillingCancelManualPurchaseRequest,
    BillingCreateManualPurchaseRequest,
    BillingPurchaseSnapshot,
    BillingUserBillingSummaryResponse,
    BillingUserSearchResponse,
)
from src.service.billing_admin_user_billing_api_client import (
    BillingAdminUserBillingApiClient,
    get_billing_admin_user_billing_api_client,
)

router = APIRouter(prefix="/api/admin/billing", tags=["billing-admin-user"])


@router.get(
    "/users/search",
    response_model=BillingUserSearchResponse,
    summary="Search users for manual billing",
)
async def search_billing_users(
    keyword: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    api_client: Annotated[
        BillingAdminUserBillingApiClient,
        Depends(get_billing_admin_user_billing_api_client),
    ] = ...,
) -> BillingUserSearchResponse:
    """GET /api/admin/billing/users/search."""

    return await api_client.search_users(keyword=keyword, limit=limit)


@router.get(
    "/users/{user_id}/billing-summary",
    response_model=BillingUserBillingSummaryResponse,
    summary="Get billing summary for one user",
)
async def get_user_billing_summary(
    user_id: int,
    api_client: Annotated[
        BillingAdminUserBillingApiClient,
        Depends(get_billing_admin_user_billing_api_client),
    ] = ...,
) -> BillingUserBillingSummaryResponse:
    """GET /api/admin/billing/users/{user_id}/billing-summary."""

    return await api_client.get_user_billing_summary(user_id)


@router.post(
    "/users/{user_id}/manual-purchases",
    response_model=BillingPurchaseSnapshot,
    status_code=201,
    summary="Create one admin-manual purchase for a user",
)
async def create_manual_purchase(
    user_id: int,
    payload: BillingCreateManualPurchaseRequest,
    api_client: Annotated[
        BillingAdminUserBillingApiClient,
        Depends(get_billing_admin_user_billing_api_client),
    ] = ...,
) -> BillingPurchaseSnapshot:
    """POST /api/admin/billing/users/{user_id}/manual-purchases."""

    return await api_client.create_manual_purchase(user_id=user_id, payload=payload)


@router.post(
    "/manual-purchases/{purchase_id}/cancel",
    response_model=BillingPurchaseSnapshot,
    summary="Cancel one admin-manual purchase",
)
async def cancel_manual_purchase(
    purchase_id: int,
    payload: BillingCancelManualPurchaseRequest,
    api_client: Annotated[
        BillingAdminUserBillingApiClient,
        Depends(get_billing_admin_user_billing_api_client),
    ] = ...,
) -> BillingPurchaseSnapshot:
    """POST /api/admin/billing/manual-purchases/{purchase_id}/cancel."""

    return await api_client.cancel_manual_purchase(
        purchase_id=purchase_id,
        payload=payload,
    )
