"""Tests for inventory diff."""

from datetime import UTC, datetime

from github_repo_inventory.diff import diff_snapshots
from github_repo_inventory.models import (
    InventorySnapshot,
    RepoInventoryRecord,
    RepoSource,
    SyncRunSummary,
)


def _summary(run_id: str) -> SyncRunSummary:
    now = datetime.now(tz=UTC)
    return SyncRunSummary(
        run_id=run_id,
        started_at=now,
        completed_at=now,
        authenticated_user="user",
        organizations=["acme"],
        total_repositories=1,
        successful_repositories=1,
        partial_repositories=0,
        failed_repositories=0,
    )


def _repo(full_name: str, pr_count: int = 0) -> RepoInventoryRecord:
    owner, name = full_name.split("/", 1)
    return RepoInventoryRecord(
        full_name=full_name,
        name=name,
        owner_login=owner,
        owner_type="Organization",
        source=RepoSource.ORGANIZATION,
        source_name=owner,
        html_url=f"https://github.com/{full_name}",
        visibility="private",
        is_private=True,
        open_pull_request_count=pr_count,
        fetched_at=datetime.now(tz=UTC),
    )


def test_diff_detects_added_removed_changed():
    base = InventorySnapshot(
        summary=_summary("run-a"),
        repositories=[_repo("acme/alpha", 0), _repo("acme/beta", 1)],
    )
    compare = InventorySnapshot(
        summary=_summary("run-b"),
        repositories=[_repo("acme/alpha", 2), _repo("acme/gamma", 0)],
    )

    result = diff_snapshots(base, compare)
    assert result.added == ["acme/gamma"]
    assert result.removed == ["acme/beta"]
    assert len(result.changed) == 1
    assert result.changed[0].full_name == "acme/alpha"
    assert "open_pull_request_count" in result.changed[0].changed_fields
