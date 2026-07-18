"""Tests for staleness scoring."""

from datetime import UTC, datetime, timedelta

from github_repo_inventory.config import ScoringConfig
from github_repo_inventory.models import (
    BranchProtection,
    MergeSettings,
    OpenPullRequest,
    RepoInventoryRecord,
    RepoSource,
    SecurityFeatures,
)
from github_repo_inventory.scoring import compute_staleness


def _repo(**overrides) -> RepoInventoryRecord:
    base = {
        "full_name": "acme/demo",
        "name": "demo",
        "owner_login": "acme",
        "owner_type": "Organization",
        "source": RepoSource.ORGANIZATION,
        "source_name": "acme",
        "html_url": "https://github.com/acme/demo",
        "visibility": "private",
        "is_private": True,
        "fetched_at": datetime.now(tz=UTC),
    }
    base.update(overrides)
    return RepoInventoryRecord(**base)


def test_inactive_repo_increases_score():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    repo = _repo(pushed_at=now - timedelta(days=400))
    scored = compute_staleness(repo, ScoringConfig(), now)
    assert scored.is_inactive is True
    assert scored.staleness_score >= 30


def test_archived_and_unprotected_and_dependabot_scores_without_disabled_security_tools():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    repo = _repo(
        pushed_at=now - timedelta(days=500),
        is_archived=True,
        branch_protection=BranchProtection(enabled=False),
        open_pull_requests=[
            OpenPullRequest(
                number=1,
                title="Bump lodash",
                author_login="dependabot[bot]",
                is_dependabot=True,
                url="https://github.com/acme/demo/pull/1",
            )
        ],
        security=SecurityFeatures(
            dependabot_alerts_enabled=False,
            secret_scanning_enabled=False,
            open_secret_scanning_alert_count=0,
        ),
        merge_settings=MergeSettings(),
    )
    scored = compute_staleness(repo, ScoringConfig(), now)
    assert scored.staleness_score == 85
    assert "no_security_features" not in {factor.id for factor in scored.staleness_factors}


def test_open_secret_scanning_alerts_adds_staleness_factor():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    repo = _repo(security=SecurityFeatures(open_secret_scanning_alert_count=3))
    scored = compute_staleness(repo, ScoringConfig(), now)
    assert any(factor.id == "open_secret_scanning_alerts" for factor in scored.staleness_factors)
    assert scored.staleness_score >= 15
