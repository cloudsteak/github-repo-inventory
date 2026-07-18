"""Pydantic configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class ScoringWeights(BaseModel):
    no_recent_push: int = 30
    archived: int = 25
    no_branch_protection: int = 20
    open_dependabot_prs: int = 10
    open_secret_scanning_alerts: int = 15


class ScoringConfig(BaseModel):
    inactive_days_threshold: int = 365
    weights: ScoringWeights = Field(default_factory=ScoringWeights)


class SyncConfig(BaseModel):
    concurrency: int = 5
    max_retries: int = 3


class StorageConfig(BaseModel):
    database: Path = Path("data/inventory.db")
    json_export: Path = Path("data/inventory.json")
    csv_export: Path = Path("data/inventory.csv")
    runs_dir: Path = Path("data/runs")
    auto_publish_dashboard: bool = True
    dashboard_json: Path = Path("dashboard/public/inventory.json")
    dashboard_csv: Path = Path("dashboard/public/inventory.csv")


class GitHubConfig(BaseModel):
    token_env: str = "GITHUB_TOKEN"
    user: str
    organizations: list[str] = Field(default_factory=list)
    include_forks: bool = True
    include_archived: bool = True
    additional_users: list[str] = Field(default_factory=list)

    @field_validator("organizations", "additional_users", mode="before")
    @classmethod
    def normalize_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        return [str(item).strip() for item in value if str(item).strip()]


class AppConfig(BaseModel):
    github: GitHubConfig
    storage: StorageConfig = Field(default_factory=StorageConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)


def load_config(path: Path) -> AppConfig:
    """Load YAML configuration from disk."""
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return AppConfig.model_validate(raw)


def resolve_paths(config: AppConfig, project_root: Path) -> AppConfig:
    """Resolve relative storage paths against the project root."""
    config.storage.database = (project_root / config.storage.database).resolve()
    config.storage.json_export = (project_root / config.storage.json_export).resolve()
    config.storage.csv_export = (project_root / config.storage.csv_export).resolve()
    config.storage.runs_dir = (project_root / config.storage.runs_dir).resolve()
    config.storage.dashboard_json = (project_root / config.storage.dashboard_json).resolve()
    config.storage.dashboard_csv = (project_root / config.storage.dashboard_csv).resolve()
    return config
