"""Staleness score calculation."""

from __future__ import annotations

from datetime import UTC, datetime

from github_repo_inventory.config import ScoringConfig
from github_repo_inventory.models import RepoInventoryRecord, StalenessFactor


def _days_since(dt: datetime | None, now: datetime) -> int | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return max(0, (now - dt).days)


def _build_staleness_factors(record: RepoInventoryRecord, config: ScoringConfig) -> list[StalenessFactor]:
    weights = config.weights
    factors: list[StalenessFactor] = []

    if record.is_inactive:
        factors.append(
            StalenessFactor(
                id="no_recent_push",
                label="Inactive repository",
                points=weights.no_recent_push,
                hint=(
                    f"No push for {record.days_since_last_push or '?'} days. "
                    "Push a commit or archive the repository if it is no longer maintained."
                ),
            )
        )
    if record.is_archived:
        factors.append(
            StalenessFactor(
                id="archived",
                label="Archived repository",
                points=weights.archived,
                hint="Repository is archived. Consider deleting or documenting if it is obsolete.",
            )
        )
    if not record.branch_protection.enabled:
        factors.append(
            StalenessFactor(
                id="no_branch_protection",
                label="No branch protection",
                points=weights.no_branch_protection,
                hint="Enable branch protection on the default branch: Settings → Branches → Branch protection rules.",
            )
        )
    if any(pr.is_dependabot for pr in record.open_pull_requests):
        dependabot_count = sum(1 for pr in record.open_pull_requests if pr.is_dependabot)
        factors.append(
            StalenessFactor(
                id="open_dependabot_prs",
                label="Open Dependabot PRs",
                points=weights.open_dependabot_prs,
                hint=f"{dependabot_count} open Dependabot PR(s). Review, merge, or close them.",
            )
        )

    open_secrets = record.security.open_secret_scanning_alert_count
    if open_secrets is not None and open_secrets > 0:
        factors.append(
            StalenessFactor(
                id="open_secret_scanning_alerts",
                label="Leaked secrets detected",
                points=weights.open_secret_scanning_alerts,
                hint=(
                    f"Secret scanning found {open_secrets} open alert(s) in this repository. "
                    "Revoke the exposed credentials and mark alerts as resolved: "
                    "Settings → Code security and analysis → Secret scanning alerts."
                ),
            )
        )

    return factors


def compute_staleness(record: RepoInventoryRecord, config: ScoringConfig, now: datetime) -> RepoInventoryRecord:
    """Compute staleness metrics and score for a repository record."""
    days = _days_since(record.pushed_at or record.updated_at, now)
    record.days_since_last_push = days
    record.is_inactive = days is not None and days >= config.inactive_days_threshold

    record.staleness_factors = _build_staleness_factors(record, config)
    record.staleness_score = min(100.0, sum(factor.points for factor in record.staleness_factors))
    return record
