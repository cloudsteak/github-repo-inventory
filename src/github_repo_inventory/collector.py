"""Repository discovery and enrichment."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

from github_repo_inventory.config import AppConfig
from github_repo_inventory.github_client import GitHubAPIError, GitHubClient
from github_repo_inventory.models import (
    BranchProtection,
    Collaborator,
    MergeSettings,
    OpenPullRequest,
    RepoInventoryRecord,
    RepoSource,
    SecurityFeatures,
    SyncRunSummary,
    TeamAccess,
)
from github_repo_inventory.scoring import compute_staleness

logger = logging.getLogger(__name__)

DEPENDABOT_LOGINS = {"dependabot[bot]", "dependabot-preview[bot]"}

REPO_LIST_QUERY = """
query($cursor: String, $query: String!) {
  search(query: $query, type: REPOSITORY, first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on Repository {
        nameWithOwner
      }
    }
  }
}
"""

REPO_DETAILS_QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    name
    nameWithOwner
    url
    isPrivate
    visibility
    isArchived
    isDisabled
    isFork
    isTemplate
    createdAt
    updatedAt
    pushedAt
    forkCount
    diskUsage
    viewerPermission
    deleteBranchOnMerge
    mergeCommitAllowed
    squashMergeAllowed
    rebaseMergeAllowed
    defaultBranchRef {
      name
      branchProtectionRule {
        requiresApprovingReviews
        requiredApprovingReviewCount
        requiresStatusChecks
        requiredStatusCheckContexts
        isAdminEnforced
        allowsForcePushes
        allowsDeletions
      }
    }
    owner {
      login
      __typename
    }
    parent {
      nameWithOwner
    }
    primaryLanguage {
      name
    }
    licenseInfo {
      name
      spdxId
    }
    repositoryTopics(first: 20) {
      nodes {
        topic {
          name
        }
      }
    }
    refs(refPrefix: "refs/heads/", first: 1) {
      totalCount
    }
    pullRequests(states: OPEN, first: 100, orderBy: {field: CREATED_AT, direction: DESC}) {
      totalCount
      nodes {
        number
        title
        createdAt
        url
        author {
          login
        }
      }
    }
    issues(states: OPEN, first: 1) {
      totalCount
    }
  }
}
"""


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _viewer_role(owner_login: str, authenticated_user: str, viewer_permission: str | None) -> tuple[bool, str | None]:
    if owner_login.lower() == authenticated_user.lower():
        return True, "OWNER"
    return False, viewer_permission


class RepoCollector:
    """Collect repository inventory across configured sources."""

    def __init__(self, client: GitHubClient, config: AppConfig, authenticated_user: str) -> None:
        self.client = client
        self.config = config
        self.authenticated_user = authenticated_user

    def collect(self) -> tuple[list[RepoInventoryRecord], SyncRunSummary]:
        started_at = datetime.now(tz=UTC)
        run_id = started_at.strftime("%Y%m%dT%H%M%SZ")
        repo_refs, discovery_errors = self._discover_repositories()
        records: list[RepoInventoryRecord] = []
        global_errors: list[str] = list(discovery_errors)

        with ThreadPoolExecutor(max_workers=self.config.sync.concurrency) as executor:
            futures = {
                executor.submit(self._collect_repo, full_name, source, source_name): full_name
                for full_name, source, source_name in repo_refs
            }
            for future in as_completed(futures):
                full_name = futures[future]
                try:
                    records.append(future.result())
                except Exception as exc:  # noqa: BLE001 - capture per-repo failures
                    logger.exception("Failed to collect %s", full_name)
                    global_errors.append(f"{full_name}: {exc}")

        now = datetime.now(tz=UTC)
        records = [
            compute_staleness(record, self.config.scoring, now)
            for record in sorted(records, key=lambda item: item.full_name.lower())
        ]

        partial_count = sum(1 for record in records if record.partial)
        failed_count = len(global_errors)
        summary = SyncRunSummary(
            run_id=run_id,
            started_at=started_at,
            completed_at=now,
            authenticated_user=self.authenticated_user,
            organizations=self.config.github.organizations,
            total_repositories=len(records) + failed_count,
            successful_repositories=len(records) - partial_count,
            partial_repositories=partial_count,
            failed_repositories=failed_count,
            errors=global_errors,
        )
        return records, summary

    def _discover_repositories(self) -> tuple[list[tuple[str, RepoSource, str]], list[str]]:
        discovered: dict[str, tuple[RepoSource, str]] = {}
        errors: list[str] = []

        def add(full_name: str, source: RepoSource, source_name: str) -> None:
            if full_name not in discovered:
                discovered[full_name] = (source, source_name)

        user_login = self.config.github.user or self.authenticated_user
        try:
            for full_name in self._list_user_repos(user_login):
                add(full_name, RepoSource.USER, user_login)
        except GitHubAPIError as exc:
            logger.error("Failed to list user repos for %s: %s", user_login, exc)
            errors.append(f"user {user_login}: {exc}")

        for username in self.config.github.additional_users:
            try:
                for full_name in self._list_user_repos(username):
                    add(full_name, RepoSource.ADDITIONAL_USER, username)
            except GitHubAPIError as exc:
                logger.error("Failed to list user repos for %s: %s", username, exc)
                errors.append(f"user {username}: {exc}")

        for org in self.config.github.organizations:
            try:
                for full_name in self._list_org_repos(org):
                    add(full_name, RepoSource.ORGANIZATION, org)
            except GitHubAPIError as exc:
                logger.error("Failed to list org repos for %s: %s", org, exc)
                errors.append(f"organization {org}: {exc}")

        refs = [(name, source, source_name) for name, (source, source_name) in discovered.items()]
        return refs, errors

    def _list_user_repos(self, username: str) -> list[str]:
        repos = self.client.paginate(f"/users/{username}/repos", params={"type": "all", "sort": "full_name"})
        return self._filter_repo_list(repos)

    def _list_org_repos(self, org: str) -> list[str]:
        repos = self.client.paginate(f"/orgs/{org}/repos", params={"type": "all", "sort": "full_name"})
        return self._filter_repo_list(repos)

    def _filter_repo_list(self, repos: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        for repo in repos:
            if not self.config.github.include_archived and repo.get("archived"):
                continue
            if not self.config.github.include_forks and repo.get("fork"):
                continue
            names.append(repo["full_name"])
        return names

    def _collect_repo(self, full_name: str, source: RepoSource, source_name: str) -> RepoInventoryRecord:
        owner, name = full_name.split("/", 1)
        errors: list[str] = []
        fetched_at = datetime.now(tz=UTC)

        try:
            details = self.client.graphql(REPO_DETAILS_QUERY, {"owner": owner, "name": name})["repository"]
        except GitHubAPIError as exc:
            return self._fallback_record(full_name, source, source_name, fetched_at, [str(exc)])

        if details is None:
            return self._fallback_record(full_name, source, source_name, fetched_at, ["Repository not found"])

        record = self._record_from_graphql(details, source, source_name, fetched_at)

        # REST enrichments that GraphQL does not fully cover or need explicit endpoints
        self._enrich_collaborators(record, errors)
        self._enrich_teams(record, errors)
        self._enrich_security(record, errors)
        self._enrich_actions(record, errors)
        self._enrich_default_merge_method(record, errors)

        record.fetch_errors = errors
        record.partial = bool(errors)
        return record

    def _record_from_graphql(
        self,
        details: dict[str, Any],
        source: RepoSource,
        source_name: str,
        fetched_at: datetime,
    ) -> RepoInventoryRecord:
        owner = details["owner"]
        owner_login = owner["login"]
        is_owner, viewer_role = _viewer_role(owner_login, self.authenticated_user, details.get("viewerPermission"))

        protection_rule = (details.get("defaultBranchRef") or {}).get("branchProtectionRule")
        branch_protection = BranchProtection(
            enabled=protection_rule is not None,
            requires_approving_reviews=(
                protection_rule.get("requiresApprovingReviews") if protection_rule else None
            ),
            required_approving_review_count=(
                protection_rule.get("requiredApprovingReviewCount") if protection_rule else None
            ),
            requires_status_checks=(
                protection_rule.get("requiresStatusChecks") if protection_rule else None
            ),
            required_status_check_contexts=(
                protection_rule.get("requiredStatusCheckContexts") or [] if protection_rule else []
            ),
            enforce_admins=protection_rule.get("isAdminEnforced") if protection_rule else None,
            allows_force_pushes=protection_rule.get("allowsForcePushes") if protection_rule else None,
            allows_deletions=protection_rule.get("allowsDeletions") if protection_rule else None,
        )

        open_prs: list[OpenPullRequest] = []
        pr_nodes = details.get("pullRequests", {}).get("nodes") or []
        for node in pr_nodes:
            author_login = (node.get("author") or {}).get("login") or "unknown"
            open_prs.append(
                OpenPullRequest(
                    number=node["number"],
                    title=node["title"],
                    author_login=author_login,
                    is_dependabot=author_login in DEPENDABOT_LOGINS,
                    created_at=_parse_datetime(node.get("createdAt")),
                    url=node["url"],
                )
            )

        topics = [
            item["topic"]["name"]
            for item in (details.get("repositoryTopics") or {}).get("nodes") or []
            if item.get("topic")
        ]

        license_info = details.get("licenseInfo") or {}
        primary_language = (details.get("primaryLanguage") or {}).get("name")

        return RepoInventoryRecord(
            full_name=details["nameWithOwner"],
            name=details["name"],
            owner_login=owner_login,
            owner_type=owner.get("__typename", "Unknown"),
            source=source,
            source_name=source_name,
            html_url=details["url"],
            visibility=details.get("visibility") or ("PRIVATE" if details.get("isPrivate") else "PUBLIC"),
            is_private=details.get("isPrivate", False),
            is_archived=details.get("isArchived", False),
            is_disabled=details.get("isDisabled", False),
            is_fork=details.get("isFork", False),
            is_template=details.get("isTemplate", False),
            created_at=_parse_datetime(details.get("createdAt")),
            updated_at=_parse_datetime(details.get("updatedAt")),
            pushed_at=_parse_datetime(details.get("pushedAt")),
            is_owner=is_owner,
            viewer_role=viewer_role,
            fork_source=(details.get("parent") or {}).get("nameWithOwner"),
            forks_count=details.get("forkCount") or 0,
            default_branch=(details.get("defaultBranchRef") or {}).get("name"),
            branch_count=(details.get("refs") or {}).get("totalCount") or 0,
            branch_protection=branch_protection,
            open_pull_requests=open_prs,
            open_pull_request_count=details.get("pullRequests", {}).get("totalCount") or len(open_prs),
            open_issue_count=details.get("issues", {}).get("totalCount") or 0,
            merge_settings=MergeSettings(
                allow_merge_commit=details.get("mergeCommitAllowed", True),
                allow_squash_merge=details.get("squashMergeAllowed", True),
                allow_rebase_merge=details.get("rebaseMergeAllowed", True),
                delete_branch_on_merge=details.get("deleteBranchOnMerge", False),
            ),
            primary_language=primary_language,
            topics=topics,
            license_spdx=license_info.get("spdxId"),
            license_name=license_info.get("name"),
            size_kb=details.get("diskUsage") or 0,
            fetched_at=fetched_at,
        )

    def _fallback_record(
        self,
        full_name: str,
        source: RepoSource,
        source_name: str,
        fetched_at: datetime,
        errors: list[str],
    ) -> RepoInventoryRecord:
        owner, name = full_name.split("/", 1)
        return RepoInventoryRecord(
            full_name=full_name,
            name=name,
            owner_login=owner,
            owner_type="Unknown",
            source=source,
            source_name=source_name,
            html_url=f"https://github.com/{full_name}",
            visibility="UNKNOWN",
            is_private=False,
            fetched_at=fetched_at,
            fetch_errors=errors,
            partial=True,
        )

    def _enrich_collaborators(self, record: RepoInventoryRecord, errors: list[str]) -> None:
        try:
            collaborators = self.client.paginate(
                f"/repos/{record.full_name}/collaborators",
                params={"affiliation": "direct"},
            )
            normalized: list[Collaborator] = []
            for item in collaborators:
                permission = item.get("role_name")
                if not permission:
                    perms = item.get("permissions") or {}
                    if perms.get("admin"):
                        permission = "admin"
                    elif perms.get("maintain"):
                        permission = "maintain"
                    elif perms.get("push"):
                        permission = "write"
                    elif perms.get("triage"):
                        permission = "triage"
                    else:
                        permission = "read"
                normalized.append(Collaborator(login=item["login"], permission=permission))
            record.collaborators = normalized
        except GitHubAPIError as exc:
            if exc.status_code != 404:
                errors.append(f"collaborators: {exc}")

    def _enrich_teams(self, record: RepoInventoryRecord, errors: list[str]) -> None:
        if record.owner_type != "Organization":
            return
        try:
            teams = self.client.get_json(f"/repos/{record.full_name}/teams")
            record.teams = [
                TeamAccess(slug=team["slug"], name=team["name"], permission=team.get("permission", "unknown"))
                for team in teams or []
            ]
        except GitHubAPIError as exc:
            if exc.status_code != 404:
                errors.append(f"teams: {exc}")

    def _enrich_security(self, record: RepoInventoryRecord, errors: list[str]) -> None:
        security = SecurityFeatures()
        owner, name = record.full_name.split("/", 1)

        try:
            self.client.request("GET", f"/repos/{record.full_name}/vulnerability-alerts", expected_status=(204, 404))
            security.dependabot_alerts_enabled = True
        except GitHubAPIError as exc:
            if exc.status_code == 404:
                security.dependabot_alerts_enabled = False
            else:
                errors.append(f"dependabot_alerts: {exc}")

        try:
            fixes = self.client.get_json(
                f"/repos/{record.full_name}/automated-security-fixes",
                expected_status=(200, 404),
            )
            security.dependabot_security_updates_enabled = fixes is not None and fixes.get("enabled", False)
        except GitHubAPIError as exc:
            if exc.status_code != 404:
                errors.append(f"dependabot_security_updates: {exc}")

        try:
            repo_meta = self.client.get_json(f"/repos/{owner}/{name}")
            security_features = (repo_meta or {}).get("security_and_analysis") or {}
            advanced = security_features.get("advanced_security") or {}
            secret = security_features.get("secret_scanning") or {}
            secret_push = security_features.get("secret_scanning_push_protection") or {}
            security.advanced_security_enabled = advanced.get("status") == "enabled"
            security.secret_scanning_enabled = secret.get("status") == "enabled"
            security.secret_scanning_push_protection_enabled = secret_push.get("status") == "enabled"
        except GitHubAPIError as exc:
            errors.append(f"security_and_analysis: {exc}")

        try:
            code_scanning = self.client.get_json(
                f"/repos/{record.full_name}/code-scanning/default-setup",
                expected_status=(200, 404, 403),
            )
            security.code_scanning_enabled = bool(code_scanning and code_scanning.get("state") == "configured")
        except GitHubAPIError as exc:
            if exc.status_code not in {403, 404}:
                errors.append(f"code_scanning: {exc}")

        record.security = security

    def _enrich_actions(self, record: RepoInventoryRecord, errors: list[str]) -> None:
        try:
            actions = self.client.get_json(f"/repos/{record.full_name}/actions/permissions", expected_status=(200, 404))
            record.actions_enabled = actions.get("enabled") if actions else None
        except GitHubAPIError as exc:
            if exc.status_code != 404:
                errors.append(f"actions: {exc}")

    def _enrich_default_merge_method(self, record: RepoInventoryRecord, errors: list[str]) -> None:
        # GitHub does not expose a single canonical default merge method on all API tiers.
        # Infer a best-effort label from allowed merge types already loaded from GraphQL.
        settings = record.merge_settings
        allowed = [
            name
            for name, enabled in (
                ("merge", settings.allow_merge_commit),
                ("squash", settings.allow_squash_merge),
                ("rebase", settings.allow_rebase_merge),
            )
            if enabled
        ]
        if len(allowed) == 1:
            settings.default_merge_method = allowed[0]
        elif allowed:
            settings.default_merge_method = "multiple"
        else:
            settings.default_merge_method = "none"
