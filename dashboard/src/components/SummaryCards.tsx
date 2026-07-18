import { RepoRecord, SyncSummary } from "../types";

interface Props {
  repos: RepoRecord[];
  summary: SyncSummary;
}

export function SummaryCards({ repos, summary }: Props) {
  const publicCount = repos.filter((repo) => !repo.is_private).length;
  const privateCount = repos.filter((repo) => repo.is_private).length;
  const archivedCount = repos.filter((repo) => repo.is_archived).length;
  const forkCount = repos.filter((repo) => repo.is_fork).length;
  const openPrCount = repos.reduce((acc, repo) => acc + repo.open_pull_request_count, 0);
  const dependabotPrCount = repos.reduce(
    (acc, repo) => acc + repo.open_pull_requests.filter((pr) => pr.is_dependabot).length,
    0,
  );
  const inactiveCount = repos.filter((repo) => repo.is_inactive).length;
  const unprotectedCount = repos.filter((repo) => !repo.branch_protection.enabled).length;
  const partialCount = repos.filter((repo) => repo.partial).length;

  const cards = [
    { label: "Visible repos", value: repos.length, hint: `${summary.total_repositories} total in run` },
    { label: "Public / Private", value: `${publicCount} / ${privateCount}` },
    { label: "Archived", value: archivedCount },
    { label: "Forks", value: forkCount },
    { label: "Open PRs", value: openPrCount, hint: `${dependabotPrCount} dependabot` },
    { label: "Inactive", value: inactiveCount },
    { label: "No branch protection", value: unprotectedCount },
    { label: "Partial sync", value: partialCount },
  ];

  return (
    <section className="cards-grid">
      {cards.map((card) => (
        <article key={card.label} className="card">
          <p className="card-label">{card.label}</p>
          <p className="card-value">{card.value}</p>
          {card.hint ? <p className="card-hint">{card.hint}</p> : null}
        </article>
      ))}
    </section>
  );
}
