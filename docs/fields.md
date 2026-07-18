# Collected Fields

This document lists the repository metadata collected in Phase 1.

## Identity

| Field | Description |
|-------|-------------|
| `full_name` | Repository slug (`owner/name`) |
| `name` | Repository name |
| `owner_login` | Owner account or organization login |
| `owner_type` | GitHub owner type (`User`, `Organization`) |
| `source` | Discovery source (`user`, `organization`, `additional_user`) |
| `source_name` | User or org login where the repo was discovered |
| `html_url` | GitHub web URL |

## Visibility and lifecycle

| Field | Description |
|-------|-------------|
| `visibility` | `PUBLIC`, `PRIVATE`, or `INTERNAL` |
| `is_private` | Private repository flag |
| `is_archived` | Archived repository flag |
| `is_disabled` | Disabled repository flag |
| `is_fork` | Fork flag |
| `is_template` | Template repository flag |
| `created_at` | Creation timestamp |
| `updated_at` | Last update timestamp |
| `pushed_at` | Last push timestamp |

## Ownership and access

| Field | Description |
|-------|-------------|
| `is_owner` | Whether the authenticated user owns the repository |
| `viewer_role` | Effective role (`OWNER`, `ADMIN`, `MAINTAIN`, `WRITE`, `READ`, etc.) |
| `collaborators` | Direct collaborators with permission level |
| `teams` | Organization teams with repository access |

## Fork metadata

| Field | Description |
|-------|-------------|
| `fork_source` | Upstream repository if forked |
| `forks_count` | Number of forks |

## Branches and protection

| Field | Description |
|-------|-------------|
| `default_branch` | Default branch name |
| `branch_count` | Number of branches |
| `branch_protection.enabled` | Whether the default branch has a protection rule |
| `branch_protection.requires_approving_reviews` | Review requirement |
| `branch_protection.required_approving_review_count` | Required approving reviews |
| `branch_protection.requires_status_checks` | Status checks required |
| `branch_protection.required_status_check_contexts` | Required check names |
| `branch_protection.enforce_admins` | Admins subject to rules |
| `branch_protection.allows_force_pushes` | Force push allowed |
| `branch_protection.allows_deletions` | Branch deletion allowed |

## Pull requests and issues

| Field | Description |
|-------|-------------|
| `open_pull_request_count` | Count of open PRs |
| `open_pull_requests[]` | Open PR number, title, author, Dependabot flag, URL |
| `open_issue_count` | Count of open issues |

## Merge settings

| Field | Description |
|-------|-------------|
| `merge_settings.delete_branch_on_merge` | Automatically delete head branches |
| `merge_settings.allow_merge_commit` | Merge commits allowed |
| `merge_settings.allow_squash_merge` | Squash merges allowed |
| `merge_settings.allow_rebase_merge` | Rebase merges allowed |
| `merge_settings.default_merge_method` | Best-effort default merge method |

## Metadata

| Field | Description |
|-------|-------------|
| `primary_language` | GitHub-detected primary language |
| `topics` | Repository topics |
| `license_name` | License common name |
| `license_spdx` | SPDX license identifier |
| `size_kb` | Repository disk usage in KB |

## Security and automation

| Field | Description |
|-------|-------------|
| `security.dependabot_alerts_enabled` | Dependabot alerts enabled |
| `security.dependabot_security_updates_enabled` | Dependabot security updates enabled |
| `security.secret_scanning_enabled` | Secret scanning enabled |
| `security.secret_scanning_push_protection_enabled` | Push protection enabled |
| `security.code_scanning_enabled` | Code scanning configured |
| `security.advanced_security_enabled` | GitHub Advanced Security enabled |
| `actions_enabled` | GitHub Actions enabled for the repository |

## Derived metrics

| Field | Description |
|-------|-------------|
| `days_since_last_push` | Days since `pushed_at` (fallback: `updated_at`) |
| `is_inactive` | True when inactivity exceeds configured threshold |
| `staleness_score` | Weighted score from 0 to 100 |

## Sync metadata

| Field | Description |
|-------|-------------|
| `fetched_at` | Timestamp when the repo record was fetched |
| `fetch_errors` | Non-fatal enrichment errors |
| `partial` | True when the record is incomplete |

## Run summary fields

Each sync run also stores:

- `run_id`
- `started_at`
- `completed_at`
- `authenticated_user`
- `organizations`
- repository success/partial/failure counts
- global errors

## Diff tracking

The `diff` command compares these tracked fields between runs:

- `visibility`
- `is_archived`
- `is_fork`
- `open_pull_request_count`
- `open_issue_count`
- `branch_count`
- `viewer_role`
- `default_branch`
- `forks_count`
- `staleness_score`
- `is_inactive`

Plus added/removed repository detection.
