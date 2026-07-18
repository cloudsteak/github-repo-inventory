"""Security feature helpers for display."""

from __future__ import annotations

from github_repo_inventory.models import SecurityFeatures

SECURITY_CHECKS = (
    (
        "dependabot_alerts_enabled",
        "Dependabot alerts",
        "Notifies you about vulnerable dependencies in the repo.",
    ),
    (
        "dependabot_security_updates_enabled",
        "Dependabot security updates",
        "Opens PRs automatically to patch vulnerable dependencies.",
    ),
    (
        "secret_scanning_enabled",
        "Secret scanning",
        "Scans commits for leaked tokens, passwords, and API keys.",
    ),
    (
        "code_scanning_enabled",
        "Code scanning",
        "Runs static analysis (e.g. CodeQL) to find code vulnerabilities.",
    ),
)


def security_status(security: SecurityFeatures) -> tuple[str, list[str]]:
    """Return (status, human-readable lines). status: ok | partial | unknown."""
    lines: list[str] = []
    values = [getattr(security, key) for key, _, _ in SECURITY_CHECKS]

    if all(value is None for value in values):
        return "unknown", [
            "Could not verify GitHub security settings (API access denied or not collected)."
        ]

    for key, name, description in SECURITY_CHECKS:
        value = getattr(security, key)
        if value is True:
            state = "ON"
        elif value is False:
            state = "OFF"
        else:
            state = "unknown"
        lines.append(f"{name}: {state} — {description}")

    open_secrets = security.open_secret_scanning_alert_count
    if open_secrets is not None and open_secrets > 0:
        lines.append(
            f"Open secret scanning alerts: {open_secrets} — leaked credentials detected in this repository."
        )

    if any(value is True for value in values):
        return "ok", lines

    return "partial", lines
