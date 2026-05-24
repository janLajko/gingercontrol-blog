"""Radar policy review API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RadarPolicySchema(BaseModel):
    """Base schema for radar policy admin APIs."""

    model_config = ConfigDict(extra="forbid")


ImpactedType = Literal[
    "deleted",
    "inserted",
    "measure_changed",
    "desc_changed",
    "rate_changed",
]


class RadarPolicyImpactRow(RadarPolicySchema):
    """One generated radar_policy_impacts row."""

    policy_update_id: int | None = None
    hts_number: str
    impacted_type: ImpactedType
    effective_time: str | None = None
    coos: list[str] | None = None
    row_desc: str | None = None


class RadarPolicyUpdateSummary(RadarPolicySchema):
    """Summary row for the review queue."""

    id: int
    source_key: str
    source_label: str
    source_url: str
    source_title: str
    headline: str
    published_at: str | None = None
    effective_date: str | None = None
    policy_extract_status: str
    policy_review_status: str
    action_calculate_status: str
    created_at: str
    updated_at: str
    measures_count: int = 0
    scope_sets_count: int = 0
    hts_modifications_count: int = 0


class RadarPolicyUpdateDetail(RadarPolicyUpdateSummary):
    """Full radar policy update for review."""

    source_metadata: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    briefing: str = ""
    impact_json: dict[str, Any] | None = None


class RadarPolicyReviewListResponse(RadarPolicySchema):
    """Pending review list response."""

    updates: list[RadarPolicyUpdateSummary]


class RadarPolicyImpactPreviewRequest(RadarPolicySchema):
    """Payload for impact preview and approval."""

    impact_json: dict[str, Any]


class RadarPolicyImpactPreviewResponse(RadarPolicySchema):
    """Generated impact preview response."""

    impacts: list[RadarPolicyImpactRow]
    count: int


class RadarPolicyUpdateDetailResponse(RadarPolicySchema):
    """Detail response wrapper."""

    update: RadarPolicyUpdateDetail


class RadarPolicyApproveResponse(RadarPolicyImpactPreviewResponse):
    """Approval response."""

    update: RadarPolicyUpdateDetail
