"""User management admin API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


EMAIL_DOMAIN = "@gingercontrol.com"


class UserManageSchema(BaseModel):
    """Base schema for user management APIs."""

    model_config = ConfigDict(extra="forbid")


class ManagedUser(UserManageSchema):
    """One row from the users table."""

    id: int
    email: str
    name: str | None = None
    avatar_url: str | None = None
    provider: str
    provider_sub: str
    company_name: str | None = None
    job_title: str | None = None
    profile_completed: bool
    email_verified: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    source: str | None = None
    callsign: str | None = None
    language: str | None = None
    password: str
    is_deleted: bool


class ManagedUserListResponse(UserManageSchema):
    """Paginated user list response."""

    items: list[ManagedUser]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)


class ManagedUserCreateRequest(UserManageSchema):
    """Create one manual gingercontrol.com user."""

    email_prefix: str = Field(..., min_length=1, max_length=128)
    name: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    job_title: str | None = Field(default=None, max_length=255)
    callsign: str | None = Field(default=None, max_length=128)
    language: str | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def validate_email_prefix(self) -> "ManagedUserCreateRequest":
        prefix = self.email_prefix.strip().lower()
        if "@" in prefix:
            raise ValueError("email_prefix must not include @")
        if any(char.isspace() for char in prefix):
            raise ValueError("email_prefix must not contain whitespace")
        if not prefix:
            raise ValueError("email_prefix is required")
        self.email_prefix = prefix
        return self


class ManagedUserDeleteResponse(UserManageSchema):
    """Soft delete response."""

    deleted: bool
    id: int
