"""Tests for dashboard publish helpers."""

from pathlib import Path

from github_repo_inventory.export import publish_dashboard_files


def test_publish_dashboard_files_copies_json_and_csv(tmp_path: Path):
    source_json = tmp_path / "data" / "inventory.json"
    source_csv = tmp_path / "data" / "inventory.csv"
    dashboard_json = tmp_path / "dashboard" / "public" / "inventory.json"
    dashboard_csv = tmp_path / "dashboard" / "public" / "inventory.csv"

    source_json.parent.mkdir(parents=True)
    source_json.write_text('{"summary": {}, "repositories": []}', encoding="utf-8")
    source_csv.write_text("full_name\n", encoding="utf-8")

    copied = publish_dashboard_files(
        json_source=source_json,
        dashboard_json=dashboard_json,
        csv_source=source_csv,
        dashboard_csv=dashboard_csv,
    )

    assert dashboard_json in copied
    assert dashboard_csv in copied
    assert dashboard_json.read_text(encoding="utf-8").startswith("{")
