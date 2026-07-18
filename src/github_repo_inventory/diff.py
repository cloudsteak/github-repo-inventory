"""Diff two inventory snapshots."""

from __future__ import annotations

from pydantic import BaseModel, Field

from github_repo_inventory.models import InventorySnapshot, RepoInventoryRecord


class RepoDiff(BaseModel):
    full_name: str
    before: RepoInventoryRecord | None = None
    after: RepoInventoryRecord | None = None
    changed_fields: list[str] = Field(default_factory=list)


class InventoryDiff(BaseModel):
    base_run_id: str
    compare_run_id: str
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    changed: list[RepoDiff] = Field(default_factory=list)


TRACKED_FIELDS = [
    "visibility",
    "is_archived",
    "is_fork",
    "open_pull_request_count",
    "open_issue_count",
    "branch_count",
    "viewer_role",
    "default_branch",
    "forks_count",
    "staleness_score",
    "is_inactive",
]


def _serialize_value(record: RepoInventoryRecord, field: str) -> object:
    if field == "visibility":
        return record.visibility
    return getattr(record, field)


def diff_snapshots(base: InventorySnapshot, compare: InventorySnapshot) -> InventoryDiff:
    base_map = {repo.full_name: repo for repo in base.repositories}
    compare_map = {repo.full_name: repo for repo in compare.repositories}

    added = sorted(set(compare_map) - set(base_map))
    removed = sorted(set(base_map) - set(compare_map))
    changed: list[RepoDiff] = []

    for full_name in sorted(set(base_map) & set(compare_map)):
        before = base_map[full_name]
        after = compare_map[full_name]
        changed_fields = [
            field for field in TRACKED_FIELDS if _serialize_value(before, field) != _serialize_value(after, field)
        ]
        if changed_fields:
            changed.append(RepoDiff(full_name=full_name, before=before, after=after, changed_fields=changed_fields))

    return InventoryDiff(
        base_run_id=base.summary.run_id,
        compare_run_id=compare.summary.run_id,
        added=added,
        removed=removed,
        changed=changed,
    )
