"""Tests for security status helpers."""

from github_repo_inventory.models import SecurityFeatures
from github_repo_inventory.security_status import security_status


def test_all_unknown_returns_unknown_status():
    status, lines = security_status(SecurityFeatures())
    assert status == "unknown"
    assert len(lines) == 1


def test_all_off_returns_partial_without_staleness_penalty_context():
    status, lines = security_status(
        SecurityFeatures(
            dependabot_alerts_enabled=False,
            dependabot_security_updates_enabled=False,
            secret_scanning_enabled=False,
            code_scanning_enabled=False,
        )
    )
    assert status == "partial"
    assert any("Dependabot alerts: OFF" in line for line in lines)


def test_open_secret_alerts_appended_to_lines():
    _, lines = security_status(
        SecurityFeatures(
            secret_scanning_enabled=True,
            open_secret_scanning_alert_count=2,
        )
    )
    assert any("Open secret scanning alerts: 2" in line for line in lines)


def test_one_on_returns_ok():
    status, _ = security_status(
        SecurityFeatures(
            dependabot_alerts_enabled=True,
            secret_scanning_enabled=False,
        )
    )
    assert status == "ok"
