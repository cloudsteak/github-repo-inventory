"""Domain models for repository inventory records."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RepoSource(StrEnum):
    USER = "user"
    ORGANIZATION = "organization"
    ADDITIONAL_USER = "additional_user"


class OpenPullRequest(BaseModel):
    number: int
    title: str
    author_login: str
    is_dependabot: bool
    created_at: datetime | None = None
    url: str


class BranchProtection(BaseModel):
    enabled: bool = False
    requires_approving_reviews: bool | None = None
    required_approving_review_count: int | None = None
    requires_status_checks: bool | None = None
    required_status_check_contexts: list[str] = Field(default_factory=list)
    enforce_admins: bool | None = None
    allows_force_pushes: bool | None = None
    allows_deletions: bool | None = None


class SecurityFeatures(BaseModel):
    dependabot_alerts_enabled: bool | None = None
    dependabot_security_updates_enabled: bool | None = None
    secret_scanning_enabled: bool | None = None
    secret_scanning_push_protection_enabled: bool | None = None
    code_scanning_enabled: bool | None = None
    advanced_security_enabled: bool | None = None
    open_secret_scanning_alert_count: int | None = None


class TeamAccess(BaseModel):
    slug: str
    name: str
    permission: str


class Collaborator(BaseModel):
    login: str
    permission: str


class MergeSettings(BaseModel):
    default_merge_method: str | None = None
    allow_merge_commit: bool = True
    allow_squash_merge: bool = True
    allow_rebase_merge: bool = True
    delete_branch_on_merge: bool = False


class StalenessFactor(BaseModel):
    id: str
    label: str
    points: float
    hint: str


class RepoInventoryRecord(BaseModel):
    # Identity
    full_name: str
    name: str
    owner_login: str
    owner_type: str
    source: RepoSource
    source_name: str
    html_url: str

    # Visibility and lifecycle
    visibility: str
    is_private: bool
    is_archived: bool = False
    is_disabled: bool = False
    is_fork: bool = False
    is_template: bool = False

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None
    pushed_at: datetime | None = None

    # Ownership and access
    is_owner: bool = False
    viewer_role: str | None = None
    collaborators: list[Collaborator] = Field(default_factory=list)
    teams: list[TeamAccess] = Field(default_factory=list)

    # Fork metadata
    fork_source: str | None = None
    forks_count: int = 0

    # Branches and protection
    default_branch: str | None = None
    branch_count: int = 0
    branch_protection: BranchProtection = Field(default_factory=BranchProtection)

    # Pull requests and issues
    open_pull_requests: list[OpenPullRequest] = Field(default_factory=list)
    open_pull_request_count: int = 0
    open_issue_count: int = 0

    # Merge settings
    merge_settings: MergeSettings = Field(default_factory=MergeSettings)

    # Metadata
    primary_language: str | None = None
    topics: list[str] = Field(default_factory=list)
    license_spdx: str | None = None
    license_name: str | None = None
    size_kb: int = 0

    # Security and automation
    security: SecurityFeatures = Field(default_factory=SecurityFeatures)
    actions_enabled: bool | None = None

    # Derived metrics
    staleness_score: float = 0.0
    staleness_factors: list[StalenessFactor] = Field(default_factory=list)
    days_since_last_push: int | None = None
    is_inactive: bool = False

    # Sync metadata
    fetched_at: datetime
    fetch_errors: list[str] = Field(default_factory=list)
    partial: bool = False


class SyncRunSummary(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    authenticated_user: str
    organizations: list[str]
    total_repositories: int
    successful_repositories: int
    partial_repositories: int
    failed_repositories: int
    errors: list[str] = Field(default_factory=list)


class InventorySnapshot(BaseModel):
    summary: SyncRunSummary
    repositories: list[RepoInventoryRecord]
