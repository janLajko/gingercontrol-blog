"""Billing admin product routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.schemas.billing_admin import (
    BillingCreateProductRequest,
    BillingFeaturePolicyListResponse,
    BillingPatchProductRequest,
    BillingProduct,
    BillingProductDetail,
    BillingProductFamily,
    BillingProductListResponse,
    BillingSyncStripeRequest,
    BillingSyncStripeResponse,
    BillingUpdateProductRequest,
    OpenApiClientListResponse,
    OpenApiClientStatus,
    OpenApiKey,
    OpenApiKeyCreateRequest,
    OpenApiKeyCreateResponse,
    OpenApiKeyListResponse,
    OpenApiKeyStatus,
)
from src.service.billing_openapi_key_admin_client import (
    BillingOpenApiKeyAdminClient,
    get_billing_openapi_key_admin_client,
)
from src.service.billing_admin_product_api_client import (
    BillingAdminProductApiClient,
    get_billing_admin_product_api_client,
)

router = APIRouter(prefix="/api/admin/billing", tags=["billing-admin"])


@router.get(
    "/feature-policies",
    response_model=BillingFeaturePolicyListResponse,
    summary="List billing feature policies",
)
async def list_billing_feature_policies(
    api_client: Annotated[
        BillingAdminProductApiClient,
        Depends(get_billing_admin_product_api_client),
    ] = ...,
) -> BillingFeaturePolicyListResponse:
    """GET /api/admin/billing/feature-policies."""

    return await api_client.list_feature_policies()


@router.get(
    "/openapi-clients",
    response_model=OpenApiClientListResponse,
    summary="List OpenAPI clients",
)
async def list_openapi_clients(
    status: OpenApiClientStatus | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    api_client: Annotated[
        BillingOpenApiKeyAdminClient,
        Depends(get_billing_openapi_key_admin_client),
    ] = ...,
) -> OpenApiClientListResponse:
    """GET /api/admin/billing/openapi-clients."""

    return await api_client.list_clients(
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/openapi-keys",
    response_model=OpenApiKeyListResponse,
    summary="List OpenAPI keys",
)
async def list_openapi_keys(
    client_id: int | None = Query(default=None, ge=1),
    status: OpenApiKeyStatus | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    api_client: Annotated[
        BillingOpenApiKeyAdminClient,
        Depends(get_billing_openapi_key_admin_client),
    ] = ...,
) -> OpenApiKeyListResponse:
    """GET /api/admin/billing/openapi-keys."""

    return await api_client.list_keys(
        client_id=client_id,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/openapi-keys",
    response_model=OpenApiKeyCreateResponse,
    status_code=201,
    summary="Create OpenAPI key",
)
async def create_openapi_key(
    payload: OpenApiKeyCreateRequest,
    api_client: Annotated[
        BillingOpenApiKeyAdminClient,
        Depends(get_billing_openapi_key_admin_client),
    ] = ...,
) -> OpenApiKeyCreateResponse:
    """POST /api/admin/billing/openapi-keys."""

    return await api_client.create_key(payload)


@router.delete(
    "/openapi-keys/{key_id}",
    response_model=OpenApiKey,
    summary="Revoke OpenAPI key",
)
async def revoke_openapi_key(
    key_id: int,
    api_client: Annotated[
        BillingOpenApiKeyAdminClient,
        Depends(get_billing_openapi_key_admin_client),
    ] = ...,
) -> OpenApiKey:
    """DELETE /api/admin/billing/openapi-keys/{key_id} revokes the key."""

    return await api_client.revoke_key(key_id)


@router.get(
    "/products",
    response_model=BillingProductListResponse,
    summary="List billing products",
)
async def list_billing_products(
    product_family: BillingProductFamily | None = Query(default=None),
    active: bool | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    api_client: Annotated[
        BillingAdminProductApiClient,
        Depends(get_billing_admin_product_api_client),
    ] = ...,
) -> BillingProductListResponse:
    """GET /api/admin/billing/products."""

    return await api_client.list_products(
        product_family=product_family,
        active=active,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/products/{product_code}",
    response_model=BillingProductDetail,
    summary="Get billing product detail",
)
async def get_billing_product(
    product_code: str,
    api_client: Annotated[
        BillingAdminProductApiClient,
        Depends(get_billing_admin_product_api_client),
    ] = ...,
) -> BillingProductDetail:
    """GET /api/admin/billing/products/{product_code}."""

    return await api_client.get_product(product_code)


@router.post(
    "/products",
    response_model=BillingProduct,
    status_code=201,
    summary="Create billing product",
)
async def create_billing_product(
    payload: BillingCreateProductRequest,
    api_client: Annotated[
        BillingAdminProductApiClient,
        Depends(get_billing_admin_product_api_client),
    ] = ...,
) -> BillingProduct:
    """POST /api/admin/billing/products."""

    return await api_client.create_product(payload)


@router.put(
    "/products/{product_code}",
    response_model=BillingProductDetail,
    summary="Replace billing product",
)
async def replace_billing_product(
    product_code: str,
    payload: BillingUpdateProductRequest,
    api_client: Annotated[
        BillingAdminProductApiClient,
        Depends(get_billing_admin_product_api_client),
    ] = ...,
) -> BillingProductDetail:
    """PUT /api/admin/billing/products/{product_code}."""

    return await api_client.replace_product(product_code, payload)


@router.patch(
    "/products/{product_code}",
    response_model=BillingProduct,
    summary="Patch billing product",
)
async def patch_billing_product(
    product_code: str,
    payload: BillingPatchProductRequest,
    api_client: Annotated[
        BillingAdminProductApiClient,
        Depends(get_billing_admin_product_api_client),
    ] = ...,
) -> BillingProduct:
    """PATCH /api/admin/billing/products/{product_code}."""

    return await api_client.patch_product(product_code, payload)


@router.post(
    "/products/{product_code}/sync-stripe",
    response_model=BillingSyncStripeResponse,
    summary="Sync billing product with Stripe",
)
async def sync_billing_product_stripe(
    product_code: str,
    payload: BillingSyncStripeRequest,
    api_client: Annotated[
        BillingAdminProductApiClient,
        Depends(get_billing_admin_product_api_client),
    ] = ...,
) -> BillingSyncStripeResponse:
    """POST /api/admin/billing/products/{product_code}/sync-stripe."""

    return await api_client.sync_stripe(product_code, payload)
