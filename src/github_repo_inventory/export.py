"""Export inventory snapshots to JSON and CSV."""

from __future__ import annotations

import csv
from pathlib import Path

from github_repo_inventory.models import InventorySnapshot, RepoInventoryRecord


def export_json(snapshot: InventorySnapshot, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")


def export_run_snapshot(snapshot: InventorySnapshot, runs_dir: Path) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    target = runs_dir / f"inventory-{snapshot.summary.run_id}.json"
    export_json(snapshot, target)
    return target


def export_csv(repositories: list[RepoInventoryRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "full_name",
        "visibility",
        "source",
        "source_name",
        "is_private",
        "is_archived",
        "is_fork",
        "is_owner",
        "viewer_role",
        "created_at",
        "updated_at",
        "pushed_at",
        "days_since_last_push",
        "is_inactive",
        "open_pull_request_count",
        "open_issue_count",
        "branch_count",
        "default_branch",
        "branch_protection_enabled",
        "fork_source",
        "forks_count",
        "primary_language",
        "license_spdx",
        "topics",
        "delete_branch_on_merge",
        "allow_merge_commit",
        "allow_squash_merge",
        "allow_rebase_merge",
        "dependabot_alerts_enabled",
        "secret_scanning_enabled",
        "code_scanning_enabled",
        "actions_enabled",
        "staleness_score",
        "partial",
        "fetch_errors",
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for repo in repositories:
            writer.writerow(
                {
                    "full_name": repo.full_name,
                    "visibility": repo.visibility,
                    "source": repo.source.value,
                    "source_name": repo.source_name,
                    "is_private": repo.is_private,
                    "is_archived": repo.is_archived,
                    "is_fork": repo.is_fork,
                    "is_owner": repo.is_owner,
                    "viewer_role": repo.viewer_role,
                    "created_at": repo.created_at.isoformat() if repo.created_at else "",
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else "",
                    "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else "",
                    "days_since_last_push": repo.days_since_last_push if repo.days_since_last_push is not None else "",
                    "is_inactive": repo.is_inactive,
                    "open_pull_request_count": repo.open_pull_request_count,
                    "open_issue_count": repo.open_issue_count,
                    "branch_count": repo.branch_count,
                    "default_branch": repo.default_branch or "",
                    "branch_protection_enabled": repo.branch_protection.enabled,
                    "fork_source": repo.fork_source or "",
                    "forks_count": repo.forks_count,
                    "primary_language": repo.primary_language or "",
                    "license_spdx": repo.license_spdx or "",
                    "topics": ";".join(repo.topics),
                    "delete_branch_on_merge": repo.merge_settings.delete_branch_on_merge,
                    "allow_merge_commit": repo.merge_settings.allow_merge_commit,
                    "allow_squash_merge": repo.merge_settings.allow_squash_merge,
                    "allow_rebase_merge": repo.merge_settings.allow_rebase_merge,
                    "dependabot_alerts_enabled": repo.security.dependabot_alerts_enabled,
                    "secret_scanning_enabled": repo.security.secret_scanning_enabled,
                    "code_scanning_enabled": repo.security.code_scanning_enabled,
                    "actions_enabled": repo.actions_enabled,
                    "staleness_score": repo.staleness_score,
                    "partial": repo.partial,
                    "fetch_errors": "; ".join(repo.fetch_errors),
                }
            )


def load_json_snapshot(path: Path) -> InventorySnapshot:
    return InventorySnapshot.model_validate_json(path.read_text(encoding="utf-8"))
