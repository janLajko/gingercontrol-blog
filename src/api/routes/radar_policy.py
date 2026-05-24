"""Radar policy review admin routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.db.radar_policy_repo import (
    RadarPolicyApiException,
    approve_radar_policy_update,
    get_radar_policy_update,
    list_pending_radar_policy_updates,
    preview_radar_policy_impacts,
)
from src.schemas.radar_policy import (
    RadarPolicyApproveResponse,
    RadarPolicyImpactPreviewRequest,
    RadarPolicyImpactPreviewResponse,
    RadarPolicyReviewListResponse,
    RadarPolicyUpdateDetailResponse,
)

router = APIRouter(prefix="/api/admin/radar-policy-updates", tags=["radar-policy"])


@router.get(
    "/review-list",
    response_model=RadarPolicyReviewListResponse,
    summary="List radar policy updates that need impact review",
)
def list_review_updates(
    limit: int = Query(default=25, ge=1, le=100),
) -> RadarPolicyReviewListResponse:
    """GET /api/admin/radar-policy-updates/review-list."""

    try:
        return RadarPolicyReviewListResponse(
            updates=list_pending_radar_policy_updates(limit)
        )
    except RadarPolicyApiException as exc:
        raise _http_exception(exc) from exc


@router.get(
    "/{policy_update_id}",
    response_model=RadarPolicyUpdateDetailResponse,
    summary="Get one radar policy update for review",
)
def get_review_update(policy_update_id: int) -> RadarPolicyUpdateDetailResponse:
    """GET /api/admin/radar-policy-updates/{policy_update_id}."""

    try:
        return RadarPolicyUpdateDetailResponse(
            update=get_radar_policy_update(policy_update_id)
        )
    except RadarPolicyApiException as exc:
        raise _http_exception(exc) from exc


@router.post(
    "/{policy_update_id}/preview-impacts",
    response_model=RadarPolicyImpactPreviewResponse,
    summary="Preview generated radar policy impacts",
)
def preview_review_impacts(
    policy_update_id: int,
    payload: RadarPolicyImpactPreviewRequest,
) -> RadarPolicyImpactPreviewResponse:
    """POST /api/admin/radar-policy-updates/{policy_update_id}/preview-impacts."""

    try:
        impacts = preview_radar_policy_impacts(
            policy_update_id,
            payload.impact_json,
        )
        return RadarPolicyImpactPreviewResponse(impacts=impacts, count=len(impacts))
    except RadarPolicyApiException as exc:
        raise _http_exception(exc) from exc


@router.post(
    "/{policy_update_id}/approve",
    response_model=RadarPolicyApproveResponse,
    summary="Approve reviewed impact_json and write radar_policy_impacts",
)
def approve_review_update(
    policy_update_id: int,
    payload: RadarPolicyImpactPreviewRequest,
) -> RadarPolicyApproveResponse:
    """POST /api/admin/radar-policy-updates/{policy_update_id}/approve."""

    try:
        update, impacts = approve_radar_policy_update(
            policy_update_id,
            payload.impact_json,
        )
        return RadarPolicyApproveResponse(
            update=update,
            impacts=impacts,
            count=len(impacts),
        )
    except RadarPolicyApiException as exc:
        raise _http_exception(exc) from exc


def _http_exception(exc: RadarPolicyApiException) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.message,
        headers={"X-Error-Code": exc.code},
    )
