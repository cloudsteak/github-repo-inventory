export interface OpenPullRequest {
  number: number;
  title: string;
  author_login: string;
  is_dependabot: boolean;
  created_at: string | null;
  url: string;
}

export interface BranchProtection {
  enabled: boolean;
  requires_approving_reviews: boolean | null;
  required_approving_review_count: number | null;
  requires_status_checks: boolean | null;
  required_status_check_contexts: string[];
  enforce_admins: boolean | null;
  allows_force_pushes: boolean | null;
  allows_deletions: boolean | null;
}

export interface SecurityFeatures {
  dependabot_alerts_enabled: boolean | null;
  dependabot_security_updates_enabled: boolean | null;
  secret_scanning_enabled: boolean | null;
  secret_scanning_push_protection_enabled: boolean | null;
  code_scanning_enabled: boolean | null;
  advanced_security_enabled: boolean | null;
}

export interface MergeSettings {
  default_merge_method: string | null;
  allow_merge_commit: boolean;
  allow_squash_merge: boolean;
  allow_rebase_merge: boolean;
  delete_branch_on_merge: boolean;
}

export interface Collaborator {
  login: string;
  permission: string;
}

export interface TeamAccess {
  slug: string;
  name: string;
  permission: string;
}

export interface RepoRecord {
  full_name: string;
  name: string;
  owner_login: string;
  owner_type: string;
  source: string;
  source_name: string;
  html_url: string;
  visibility: string;
  is_private: boolean;
  is_archived: boolean;
  is_disabled: boolean;
  is_fork: boolean;
  is_template: boolean;
  created_at: string | null;
  updated_at: string | null;
  pushed_at: string | null;
  is_owner: boolean;
  viewer_role: string | null;
  collaborators: Collaborator[];
  teams: TeamAccess[];
  fork_source: string | null;
  forks_count: number;
  default_branch: string | null;
  branch_count: number;
  branch_protection: BranchProtection;
  open_pull_requests: OpenPullRequest[];
  open_pull_request_count: number;
  open_issue_count: number;
  merge_settings: MergeSettings;
  primary_language: string | null;
  topics: string[];
  license_spdx: string | null;
  license_name: string | null;
  size_kb: number;
  security: SecurityFeatures;
  actions_enabled: boolean | null;
  staleness_score: number;
  days_since_last_push: number | null;
  is_inactive: boolean;
  fetched_at: string;
  fetch_errors: string[];
  partial: boolean;
}

export interface SyncSummary {
  run_id: string;
  started_at: string;
  completed_at: string;
  authenticated_user: string;
  organizations: string[];
  total_repositories: number;
  successful_repositories: number;
  partial_repositories: number;
  failed_repositories: number;
  errors: string[];
}

export interface InventorySnapshot {
  summary: SyncSummary;
  repositories: RepoRecord[];
}

export interface SavedView {
  id: string;
  name: string;
  search: string;
  source: string;
  visibility: string;
  archived: string;
  fork: string;
  hasOpenPr: string;
  dependabotOnly: boolean;
  inactiveOnly: boolean;
  unprotectedOnly: boolean;
  groupBy: string;
}
