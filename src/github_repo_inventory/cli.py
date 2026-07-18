"""Command-line interface."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from github_repo_inventory.collector import RepoCollector
from github_repo_inventory.config import load_config, resolve_paths
from github_repo_inventory.diff import diff_snapshots
from github_repo_inventory.export import (
    export_csv,
    export_json,
    export_run_snapshot,
    load_json_snapshot,
)
from github_repo_inventory.github_client import GitHubClient
from github_repo_inventory.models import InventorySnapshot
from github_repo_inventory.storage import InventoryDatabase

console = Console()
logger = logging.getLogger(__name__)


def _project_root() -> Path:
    return Path.cwd()


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _load_app_config(config_path: Path):
    config = load_config(config_path)
    return resolve_paths(config, _project_root())


def _load_dotenv(config_path: Path) -> None:
    """Load .env from the project root (directory containing config.yaml)."""
    env_path = config_path.resolve().parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def _get_token(config) -> str:
    token = os.environ.get(config.github.token_env)
    if not token:
        raise click.ClickException(
            f"Missing GitHub token. Set the {config.github.token_env} environment variable."
        )
    return token


@click.group()
@click.option("--config", "config_path", type=click.Path(path_type=Path), default="config.yaml")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
@click.pass_context
def main(ctx: click.Context, config_path: Path, verbose: bool) -> None:
    """Discover and inventory GitHub repositories."""
    _setup_logging(verbose)
    _load_dotenv(config_path)
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path


@main.command()
@click.pass_context
def sync(ctx: click.Context) -> None:
    """Fetch repository inventory from GitHub and persist results."""
    config = _load_app_config(ctx.obj["config_path"])
    token = _get_token(config)

    with GitHubClient(token, max_retries=config.sync.max_retries) as client:
        authenticated_user = client.get_authenticated_login()
        if not config.github.user:
            config.github.user = authenticated_user

        console.print(f"[bold]Syncing repositories for[/bold] {config.github.user}")
        if config.github.organizations:
            console.print(f"Organizations: {', '.join(config.github.organizations)}")

        collector = RepoCollector(client, config, authenticated_user)
        repositories, summary = collector.collect()
        snapshot = InventorySnapshot(summary=summary, repositories=repositories)

        db = InventoryDatabase(config.storage.database)
        db.save_snapshot(snapshot)
        export_json(snapshot, config.storage.json_export)
        run_path = export_run_snapshot(snapshot, config.storage.runs_dir)

    console.print(
        f"[green]Done.[/green] {summary.successful_repositories} ok, "
        f"{summary.partial_repositories} partial, {summary.failed_repositories} failed."
    )
    if summary.errors:
        console.print("[yellow]Discovery / fetch errors:[/yellow]")
        for error in summary.errors:
            console.print(f"  - {error}")
    console.print(f"JSON export: {config.storage.json_export}")
    console.print(f"Run snapshot: {run_path}")


@main.command("list-runs")
@click.pass_context
def list_runs(ctx: click.Context) -> None:
    """List stored inventory runs."""
    config = _load_app_config(ctx.obj["config_path"])
    db = InventoryDatabase(config.storage.database)
    runs = db.list_runs()
    if not runs:
        console.print("No runs found.")
        return

    table = Table(title="Inventory Runs")
    table.add_column("Run ID")
    table.add_column("Started")
    table.add_column("Repos")
    table.add_column("Partial")
    table.add_column("Failed")
    for run in runs:
        table.add_row(
            run.run_id,
            run.started_at.isoformat(),
            str(run.total_repositories),
            str(run.partial_repositories),
            str(run.failed_repositories),
        )
    console.print(table)


@main.command()
@click.option("--run-id", default=None, help="Export a specific run ID.")
@click.option("--csv", "csv_path", type=click.Path(path_type=Path), default=None, help="Optional CSV output path.")
@click.pass_context
def export(ctx: click.Context, run_id: str | None, csv_path: Path | None) -> None:
    """Export the latest or selected inventory run."""
    config = _load_app_config(ctx.obj["config_path"])
    db = InventoryDatabase(config.storage.database)
    snapshot = db.load_snapshot(run_id) if run_id else db.latest_snapshot()
    if snapshot is None:
        raise click.ClickException("No inventory snapshot found. Run `sync` first.")

    export_json(snapshot, config.storage.json_export)
    console.print(f"Exported JSON to {config.storage.json_export}")

    if csv_path:
        export_csv(snapshot.repositories, csv_path)
        console.print(f"Exported CSV to {csv_path}")


@main.command()
@click.argument("base_run_id")
@click.argument("compare_run_id")
@click.option("--json", "as_json", is_flag=True, help="Print full diff as JSON.")
@click.pass_context
def diff(ctx: click.Context, base_run_id: str, compare_run_id: str, as_json: bool) -> None:
    """Compare two inventory runs."""
    config = _load_app_config(ctx.obj["config_path"])
    db = InventoryDatabase(config.storage.database)
    base = db.load_snapshot(base_run_id)
    compare = db.load_snapshot(compare_run_id)
    if base is None or compare is None:
        raise click.ClickException("One or both run IDs were not found.")

    result = diff_snapshots(base, compare)
    if as_json:
        console.print_json(result.model_dump_json())
        return

    console.print(f"[bold]Added ({len(result.added)}):[/bold] {', '.join(result.added) or '-'}")
    console.print(f"[bold]Removed ({len(result.removed)}):[/bold] {', '.join(result.removed) or '-'}")
    console.print(f"[bold]Changed ({len(result.changed)}):[/bold]")
    for item in result.changed:
        console.print(f"  {item.full_name}: {', '.join(item.changed_fields)}")


@main.command()
@click.argument("json_path", type=click.Path(path_type=Path, exists=True))
@click.pass_context
def diff_files(ctx: click.Context, json_path: Path) -> None:
    """Compare a JSON snapshot file against the latest stored run."""
    config = _load_app_config(ctx.obj["config_path"])
    db = InventoryDatabase(config.storage.database)
    latest = db.latest_snapshot()
    if latest is None:
        raise click.ClickException("No stored run to compare against.")

    other = load_json_snapshot(json_path)
    result = diff_snapshots(other, latest)
    console.print_json(result.model_dump_json())


if __name__ == "__main__":
    try:
        main()
    except click.ClickException as exc:
        console.print(f"[red]{exc.message}[/red]")
        sys.exit(1)
