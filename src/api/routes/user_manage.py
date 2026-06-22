"""User management admin routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.db.user_manage_repo import (
    UserManageApiException,
    create_user,
    delete_user,
    get_user,
    list_users,
)
from src.schemas.user_manage import (
    ManagedUser,
    ManagedUserCreateRequest,
    ManagedUserDeleteResponse,
    ManagedUserListResponse,
)

router = APIRouter(prefix="/api/admin/users", tags=["user-manage"])


@router.get("", response_model=ManagedUserListResponse, summary="List users")
def list_managed_users(
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ManagedUserListResponse:
    """GET /api/admin/users."""

    try:
        return ManagedUserListResponse(
            **list_users(keyword=keyword, page=page, page_size=page_size)
        )
    except UserManageApiException as exc:
        raise _http_exception(exc) from exc


@router.post(
    "",
    response_model=ManagedUser,
    status_code=201,
    summary="Create user",
)
def create_managed_user(payload: ManagedUserCreateRequest) -> ManagedUser:
    """POST /api/admin/users."""

    try:
        return ManagedUser(**create_user(payload))
    except UserManageApiException as exc:
        raise _http_exception(exc) from exc


@router.get("/{user_id}", response_model=ManagedUser, summary="Get user detail")
def get_managed_user(user_id: int) -> ManagedUser:
    """GET /api/admin/users/{user_id}."""

    try:
        return ManagedUser(**get_user(user_id))
    except UserManageApiException as exc:
        raise _http_exception(exc) from exc


@router.delete(
    "/{user_id}",
    response_model=ManagedUserDeleteResponse,
    summary="Soft delete user",
)
def delete_managed_user(user_id: int) -> ManagedUserDeleteResponse:
    """DELETE /api/admin/users/{user_id}."""

    try:
        delete_user(user_id)
        return ManagedUserDeleteResponse(deleted=True, id=user_id)
    except UserManageApiException as exc:
        raise _http_exception(exc) from exc


def _http_exception(exc: UserManageApiException) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.message,
        headers={"X-Error-Code": exc.code},
    )
