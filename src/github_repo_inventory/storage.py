"""SQLite persistence for inventory snapshots."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from github_repo_inventory.models import InventorySnapshot, RepoInventoryRecord, SyncRunSummary


class InventoryDatabase:
    """SQLite storage for inventory runs and repository records."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sync_runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    authenticated_user TEXT NOT NULL,
                    organizations_json TEXT NOT NULL,
                    total_repositories INTEGER NOT NULL,
                    successful_repositories INTEGER NOT NULL,
                    partial_repositories INTEGER NOT NULL,
                    failed_repositories INTEGER NOT NULL,
                    errors_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS repositories (
                    run_id TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, full_name),
                    FOREIGN KEY (run_id) REFERENCES sync_runs(run_id)
                );

                CREATE INDEX IF NOT EXISTS idx_repositories_run_id ON repositories(run_id);
                """
            )

    def save_snapshot(self, snapshot: InventorySnapshot) -> None:
        self.initialize()
        summary = snapshot.summary
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO sync_runs (
                    run_id, started_at, completed_at, authenticated_user, organizations_json,
                    total_repositories, successful_repositories, partial_repositories,
                    failed_repositories, errors_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary.run_id,
                    summary.started_at.isoformat(),
                    summary.completed_at.isoformat(),
                    summary.authenticated_user,
                    json.dumps(summary.organizations),
                    summary.total_repositories,
                    summary.successful_repositories,
                    summary.partial_repositories,
                    summary.failed_repositories,
                    json.dumps(summary.errors),
                ),
            )
            connection.executemany(
                """
                INSERT OR REPLACE INTO repositories (run_id, full_name, payload_json)
                VALUES (?, ?, ?)
                """,
                [
                    (summary.run_id, repo.full_name, repo.model_dump_json())
                    for repo in snapshot.repositories
                ],
            )

    def list_runs(self) -> list[SyncRunSummary]:
        self.initialize()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM sync_runs ORDER BY started_at DESC"
            ).fetchall()
        return [_row_to_summary(row) for row in rows]

    def load_snapshot(self, run_id: str) -> InventorySnapshot | None:
        self.initialize()
        with self.connect() as connection:
            summary_row = connection.execute(
                "SELECT * FROM sync_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if summary_row is None:
                return None
            repo_rows = connection.execute(
                "SELECT payload_json FROM repositories WHERE run_id = ? ORDER BY full_name",
                (run_id,),
            ).fetchall()
        repositories = [RepoInventoryRecord.model_validate_json(row["payload_json"]) for row in repo_rows]
        return InventorySnapshot(summary=_row_to_summary(summary_row), repositories=repositories)

    def latest_snapshot(self) -> InventorySnapshot | None:
        runs = self.list_runs()
        if not runs:
            return None
        return self.load_snapshot(runs[0].run_id)


def _row_to_summary(row: sqlite3.Row) -> SyncRunSummary:
    return SyncRunSummary(
        run_id=row["run_id"],
        started_at=datetime.fromisoformat(row["started_at"]),
        completed_at=datetime.fromisoformat(row["completed_at"]),
        authenticated_user=row["authenticated_user"],
        organizations=json.loads(row["organizations_json"]),
        total_repositories=row["total_repositories"],
        successful_repositories=row["successful_repositories"],
        partial_repositories=row["partial_repositories"],
        failed_repositories=row["failed_repositories"],
        errors=json.loads(row["errors_json"]),
    )
