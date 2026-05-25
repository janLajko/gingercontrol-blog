"""Invitation code admin API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InvitationCodeSchema(BaseModel):
    """Base schema for invitation code APIs."""

    model_config = ConfigDict(extra="forbid")


InvitationCodeType = Literal["radar", "register", "sandbox"]
InvitationCodeStatus = Literal["active", "disabled", "expired", "exhausted"]


class InvitationCode(InvitationCodeSchema):
    """One invitation code row."""

    id: int
    code: str
    code_type: InvitationCodeType
    prefix: str
    code_length: int
    max_uses: int
    used_count: int
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    status: InvitationCodeStatus
    note: str | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
    disabled_at: datetime | None = None


class InvitationCodeUsage(InvitationCodeSchema):
    """One invitation code usage row."""

    id: int
    code: str
    user_id: str
    used_at: datetime


class InvitationCodeListResponse(InvitationCodeSchema):
    """Paginated invitation code list response."""

    items: list[InvitationCode]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)


class InvitationCodeUsageListResponse(InvitationCodeSchema):
    """Paginated invitation code usage list response."""

    items: list[InvitationCodeUsage]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)


class InvitationCodeCreateRequest(InvitationCodeSchema):
    """Create one invitation code.

    When code is omitted, the backend generates one from prefix and code_length.
    """

    code: str | None = Field(default=None, min_length=1, max_length=128)
    code_type: InvitationCodeType
    prefix: str = Field(default="", max_length=32)
    code_length: int = Field(..., gt=0, le=128)
    max_uses: int = Field(default=1, gt=0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    status: InvitationCodeStatus = "active"
    note: str | None = None
    created_by: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_code_rules(self) -> "InvitationCodeCreateRequest":
        if self.valid_from and self.valid_until and self.valid_from >= self.valid_until:
            raise ValueError("valid_from must be before valid_until")

        if self.code:
            if len(self.code) != self.code_length:
                raise ValueError("code length must equal code_length")
            if self.prefix and not self.code.startswith(self.prefix):
                raise ValueError("code must start with prefix")
        elif len(self.prefix) >= self.code_length:
            raise ValueError("prefix length must be shorter than code_length")

        return self


class InvitationCodePatchRequest(InvitationCodeSchema):
    """Patch mutable invitation code fields."""

    code_type: InvitationCodeType | None = None
    prefix: str | None = Field(default=None, max_length=32)
    code_length: int | None = Field(default=None, gt=0, le=128)
    max_uses: int | None = Field(default=None, gt=0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    status: InvitationCodeStatus | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_valid_range(self) -> "InvitationCodePatchRequest":
        if self.valid_from and self.valid_until and self.valid_from >= self.valid_until:
            raise ValueError("valid_from must be before valid_until")
        return self


class InvitationCodeDeleteResponse(InvitationCodeSchema):
    """Delete response."""

    deleted: bool
    id: int
