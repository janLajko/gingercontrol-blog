"""Invitation code admin routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.db.invitation_code_repo import (
    InvitationCodeApiException,
    create_invitation_code,
    delete_invitation_code,
    get_invitation_code,
    list_invitation_code_usages,
    list_invitation_codes,
    patch_invitation_code,
)
from src.schemas.invitation_code import (
    InvitationCode,
    InvitationCodeCreateRequest,
    InvitationCodeDeleteResponse,
    InvitationCodeListResponse,
    InvitationCodePatchRequest,
    InvitationCodeStatus,
    InvitationCodeType,
    InvitationCodeUsageListResponse,
)

router = APIRouter(prefix="/api/admin/invitation-codes", tags=["invitation-codes"])


@router.get(
    "",
    response_model=InvitationCodeListResponse,
    summary="List invitation codes",
)
def list_codes(
    code_type: InvitationCodeType | None = Query(default=None),
    status: InvitationCodeStatus | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> InvitationCodeListResponse:
    """GET /api/admin/invitation-codes."""

    try:
        return InvitationCodeListResponse(
            **list_invitation_codes(
                code_type=code_type,
                status=status,
                keyword=keyword,
                page=page,
                page_size=page_size,
            )
        )
    except InvitationCodeApiException as exc:
        raise _http_exception(exc) from exc


@router.post(
    "",
    response_model=InvitationCode,
    status_code=201,
    summary="Create invitation code",
)
def create_code(payload: InvitationCodeCreateRequest) -> InvitationCode:
    """POST /api/admin/invitation-codes."""

    try:
        return InvitationCode(**create_invitation_code(payload))
    except InvitationCodeApiException as exc:
        raise _http_exception(exc) from exc


@router.get(
    "/{invitation_code_id}",
    response_model=InvitationCode,
    summary="Get invitation code detail",
)
def get_code(invitation_code_id: int) -> InvitationCode:
    """GET /api/admin/invitation-codes/{invitation_code_id}."""

    try:
        return InvitationCode(**get_invitation_code(invitation_code_id))
    except InvitationCodeApiException as exc:
        raise _http_exception(exc) from exc


@router.patch(
    "/{invitation_code_id}",
    response_model=InvitationCode,
    summary="Patch invitation code",
)
def patch_code(
    invitation_code_id: int,
    payload: InvitationCodePatchRequest,
) -> InvitationCode:
    """PATCH /api/admin/invitation-codes/{invitation_code_id}."""

    try:
        return InvitationCode(**patch_invitation_code(invitation_code_id, payload))
    except InvitationCodeApiException as exc:
        raise _http_exception(exc) from exc


@router.delete(
    "/{invitation_code_id}",
    response_model=InvitationCodeDeleteResponse,
    summary="Delete invitation code",
)
def delete_code(invitation_code_id: int) -> InvitationCodeDeleteResponse:
    """DELETE /api/admin/invitation-codes/{invitation_code_id}."""

    try:
        delete_invitation_code(invitation_code_id)
        return InvitationCodeDeleteResponse(deleted=True, id=invitation_code_id)
    except InvitationCodeApiException as exc:
        raise _http_exception(exc) from exc


@router.get(
    "/{invitation_code_id}/usages",
    response_model=InvitationCodeUsageListResponse,
    summary="List invitation code usage records",
)
def list_code_usages(
    invitation_code_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> InvitationCodeUsageListResponse:
    """GET /api/admin/invitation-codes/{invitation_code_id}/usages."""

    try:
        return InvitationCodeUsageListResponse(
            **list_invitation_code_usages(
                invitation_code_id=invitation_code_id,
                page=page,
                page_size=page_size,
            )
        )
    except InvitationCodeApiException as exc:
        raise _http_exception(exc) from exc


def _http_exception(exc: InvitationCodeApiException) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.message,
        headers={"X-Error-Code": exc.code},
    )
