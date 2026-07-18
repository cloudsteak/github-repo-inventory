"""Staleness score calculation."""

from __future__ import annotations

from datetime import UTC, datetime

from github_repo_inventory.config import ScoringConfig
from github_repo_inventory.models import RepoInventoryRecord, SecurityFeatures


def _days_since(dt: datetime | None, now: datetime) -> int | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return max(0, (now - dt).days)


def _security_feature_count(security: SecurityFeatures) -> int:
    flags = [
        security.dependabot_alerts_enabled,
        security.dependabot_security_updates_enabled,
        security.secret_scanning_enabled,
        security.code_scanning_enabled,
    ]
    return sum(1 for flag in flags if flag is True)


def compute_staleness(record: RepoInventoryRecord, config: ScoringConfig, now: datetime) -> RepoInventoryRecord:
    """Compute staleness metrics and score for a repository record."""
    days = _days_since(record.pushed_at or record.updated_at, now)
    record.days_since_last_push = days
    record.is_inactive = days is not None and days >= config.inactive_days_threshold

    score = 0.0
    weights = config.weights

    if record.is_inactive:
        score += weights.no_recent_push
    if record.is_archived:
        score += weights.archived
    if not record.branch_protection.enabled:
        score += weights.no_branch_protection
    if any(pr.is_dependabot for pr in record.open_pull_requests):
        score += weights.open_dependabot_prs
    if _security_feature_count(record.security) == 0:
        score += weights.no_security_features

    record.staleness_score = min(100.0, score)
    return record
