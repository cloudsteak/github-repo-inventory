import { RepoRecord, SyncSummary } from "../types";
import { SUMMARY_CARDS, SummaryCardId, activeCardForView } from "../cardFilters";

interface Props {
  repos: RepoRecord[];
  allRepos: RepoRecord[];
  summary: SyncSummary;
  draftView: import("../types").SavedView;
  onCardClick: (cardId: SummaryCardId) => void;
}

export function SummaryCards({ repos, allRepos, summary, draftView, onCardClick }: Props) {
  const activeCard = activeCardForView(draftView);

  const counts: Record<SummaryCardId, number | string> = {
    all: allRepos.length,
    archived: allRepos.filter((repo) => repo.is_archived).length,
    forks: allRepos.filter((repo) => repo.is_fork).length,
    "open-prs": allRepos.reduce((acc, repo) => acc + repo.open_pull_request_count, 0),
    inactive: allRepos.filter((repo) => repo.is_inactive).length,
    unprotected: allRepos.filter((repo) => !repo.branch_protection.enabled).length,
    partial: allRepos.filter((repo) => repo.partial).length,
  };

  const dependabotPrCount = allRepos.reduce(
    (acc, repo) => acc + repo.open_pull_requests.filter((pr) => pr.is_dependabot).length,
    0,
  );

  const publicCount = allRepos.filter((repo) => !repo.is_private).length;
  const privateCount = allRepos.filter((repo) => repo.is_private).length;
  const sourceBreakdown = allRepos.reduce<Record<string, number>>((acc, repo) => {
    acc[repo.source_name] = (acc[repo.source_name] ?? 0) + 1;
    return acc;
  }, {});
  const sourceHint = Object.entries(sourceBreakdown)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, count]) => `${name}: ${count}`)
    .join(" · ");

  return (
    <section className="cards-grid">
      <article
        className={`card card-filterable ${activeCard === "all" ? "card-active" : ""}`}
        role="button"
        tabIndex={0}
        onClick={() => onCardClick("all")}
        onKeyDown={(event) => event.key === "Enter" && onCardClick("all")}
        title="Show all repositories"
      >
        <p className="card-label">Visible repos</p>
        <p className="card-value">{repos.length === allRepos.length ? counts.all : `${repos.length} / ${counts.all}`}</p>
        <p className="card-hint">
          {summary.total_repositories} total in run · {sourceHint || "No sources"}
        </p>
        <p className="card-hint">Public / Private: {publicCount} / {privateCount}</p>
      </article>

      {SUMMARY_CARDS.filter((card) => card.id !== "all").map((card) => (
        <article
          key={card.id}
          className={`card card-filterable ${activeCard === card.id ? "card-active" : ""}`}
          role="button"
          tabIndex={0}
          onClick={() => onCardClick(card.id)}
          onKeyDown={(event) => event.key === "Enter" && onCardClick(card.id)}
          title={`Filter: ${card.label}`}
        >
          <p className="card-label">{card.label}</p>
          <p className="card-value">{counts[card.id]}</p>
          {card.id === "open-prs" ? <p className="card-hint">{dependabotPrCount} dependabot PRs</p> : null}
          {card.id === "inactive" && activeCard !== "inactive" ? (
            <p className="card-hint">Click to filter</p>
          ) : null}
        </article>
      ))}
    </section>
  );
}
