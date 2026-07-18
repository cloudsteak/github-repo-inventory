import { RepoRecord, SecurityFeatures, StalenessFactor } from "./types";

const DEFAULT_WEIGHTS = {
  no_recent_push: 30,
  archived: 25,
  no_branch_protection: 20,
  open_dependabot_prs: 10,
  open_secret_scanning_alerts: 15,
};

const INACTIVE_DAYS = 365;

export const SECURITY_CHECKS: {
  key: keyof SecurityFeatures;
  name: string;
  description: string;
}[] = [
  {
    key: "dependabot_alerts_enabled",
    name: "Dependabot alerts",
    description: "Notifies you about vulnerable dependencies.",
  },
  {
    key: "dependabot_security_updates_enabled",
    name: "Dependabot security updates",
    description: "Opens PRs to patch vulnerable dependencies.",
  },
  {
    key: "secret_scanning_enabled",
    name: "Secret scanning",
    description: "Scans commits for leaked tokens and passwords.",
  },
  {
    key: "code_scanning_enabled",
    name: "Code scanning",
    description: "Static analysis (e.g. CodeQL) for code vulnerabilities.",
  },
];

export function securityStatusLines(security: SecurityFeatures): {
  status: "ok" | "partial" | "unknown";
  lines: string[];
} {
  const values = SECURITY_CHECKS.map((check) => security[check.key]);

  if (values.every((value) => value === null || value === undefined)) {
    return {
      status: "unknown",
      lines: ["Could not verify GitHub security settings (not collected or API access denied)."],
    };
  }

  const lines = SECURITY_CHECKS.map((check) => {
    const value = security[check.key];
    const state = value === true ? "ON" : value === false ? "OFF" : "unknown";
    return `${check.name}: ${state} — ${check.description}`;
  });

  const openSecrets = security.open_secret_scanning_alert_count;
  if (openSecrets != null && openSecrets > 0) {
    lines.push(
      `Open secret scanning alerts: ${openSecrets} — leaked credentials detected in this repository.`,
    );
  }

  if (values.some((value) => value === true)) {
    return { status: "ok", lines };
  }

  return { status: "partial", lines };
}

function buildSecretStalenessFactor(repo: RepoRecord): StalenessFactor | null {
  const count = repo.security.open_secret_scanning_alert_count;
  if (count == null || count <= 0) {
    return null;
  }

  return {
    id: "open_secret_scanning_alerts",
    label: "Leaked secrets detected",
    points: DEFAULT_WEIGHTS.open_secret_scanning_alerts,
    hint: [
      `Secret scanning found ${count} open alert(s) in this repository.`,
      "Revoke the exposed credentials and resolve alerts under:",
      "Settings → Code security and analysis → Secret scanning alerts.",
    ].join("\n"),
  };
}

function enrichFactor(repo: RepoRecord, factor: StalenessFactor): StalenessFactor {
  if (factor.id === "open_secret_scanning_alerts") {
    return buildSecretStalenessFactor(repo) ?? factor;
  }
  if (factor.id === "no_security_features") {
    return buildSecretStalenessFactor(repo) ?? { ...factor, points: 0, label: "(removed)" };
  }
  return factor;
}

/** Compute staleness breakdown (uses stored factors when present, otherwise derives from repo fields). */
export function getStalenessFactors(repo: RepoRecord): StalenessFactor[] {
  const raw = repo.staleness_factors?.length
    ? repo.staleness_factors
        .filter((factor) => factor.id !== "no_security_features")
        .map((factor) => enrichFactor(repo, factor))
        .filter((factor) => factor.points > 0)
    : buildDerivedFactors(repo);

  return raw;
}

function buildDerivedFactors(repo: RepoRecord): StalenessFactor[] {
  const factors: StalenessFactor[] = [];
  const dependabotCount = repo.open_pull_requests.filter((pr) => pr.is_dependabot).length;

  if (repo.is_inactive) {
    factors.push({
      id: "no_recent_push",
      label: "Inactive repository",
      points: DEFAULT_WEIGHTS.no_recent_push,
      hint: `No push for ${repo.days_since_last_push ?? "?"} days (threshold: ${INACTIVE_DAYS}). Push a commit or archive the repo.`,
    });
  }
  if (repo.is_archived) {
    factors.push({
      id: "archived",
      label: "Archived repository",
      points: DEFAULT_WEIGHTS.archived,
      hint: "Repository is archived. Consider deleting or documenting if it is obsolete.",
    });
  }
  if (!repo.branch_protection.enabled) {
    factors.push({
      id: "no_branch_protection",
      label: "No branch protection",
      points: DEFAULT_WEIGHTS.no_branch_protection,
      hint: "Enable branch protection: Settings → Branches → Branch protection rules.",
    });
  }
  if (dependabotCount > 0) {
    factors.push({
      id: "open_dependabot_prs",
      label: "Open Dependabot PRs",
      points: DEFAULT_WEIGHTS.open_dependabot_prs,
      hint: `${dependabotCount} open Dependabot PR(s). Review, merge, or close them.`,
    });
  }

  const secretFactor = buildSecretStalenessFactor(repo);
  if (secretFactor) {
    factors.push(secretFactor);
  }

  return factors;
}

export function effectiveStalenessScore(repo: RepoRecord): number {
  return Math.min(100, getStalenessFactors(repo).reduce((sum, factor) => sum + factor.points, 0));
}

export function stalenessTone(score: number): "ok" | "warn" | "danger" {
  if (score >= 70) return "danger";
  if (score >= 40) return "warn";
  return "ok";
}
