import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { InventorySnapshot, RepoRecord, SavedView } from "./types";
import { RepoTable } from "./components/RepoTable";
import { SummaryCards } from "./components/SummaryCards";
import { FilterBar } from "./components/FilterBar";
import { DEFAULT_VIEWS, loadViews, saveViews } from "./savedViews";
import { SummaryCardId, activeCardForView, viewForCard } from "./cardFilters";

const COLORS = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706", "#dc2626", "#64748b"];

async function loadInventory(): Promise<InventorySnapshot> {
  const response = await fetch(`${import.meta.env.BASE_URL}inventory.json`);
  if (!response.ok) {
    throw new Error(
      response.status === 404
        ? "inventory.json not found. Run: uv run github-repo-inventory sync"
        : `Failed to load inventory.json (${response.status})`,
    );
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    throw new Error(
      "inventory.json returned HTML instead of JSON. Restart the dev server from dashboard/ after syncing.",
    );
  }

  return response.json();
}

function applyFilters(repos: RepoRecord[], view: SavedView): RepoRecord[] {
  return repos.filter((repo) => {
    const search = view.search.trim().toLowerCase();
    if (search) {
      const haystack = [
        repo.full_name,
        repo.primary_language ?? "",
        repo.topics.join(" "),
        repo.viewer_role ?? "",
        repo.fork_source ?? "",
      ]
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(search)) return false;
    }
    if (view.source !== "all" && repo.source_name !== view.source && repo.source !== view.source) return false;
    if (view.visibility !== "all" && repo.visibility.toLowerCase() !== view.visibility) return false;
    if (view.archived === "yes" && !repo.is_archived) return false;
    if (view.archived === "no" && repo.is_archived) return false;
    if (view.fork === "yes" && !repo.is_fork) return false;
    if (view.fork === "no" && repo.is_fork) return false;
    if (view.hasOpenPr === "yes" && repo.open_pull_request_count === 0) return false;
    if (view.hasOpenPr === "no" && repo.open_pull_request_count > 0) return false;
    if (view.dependabotOnly && !repo.open_pull_requests.some((pr) => pr.is_dependabot)) return false;
    if (view.inactiveOnly && !repo.is_inactive) return false;
    if (view.unprotectedOnly && repo.branch_protection.enabled) return false;
    if (view.partialOnly && !repo.partial) return false;
    return true;
  });
}

function groupRepos(repos: RepoRecord[], groupBy: string): Record<string, RepoRecord[]> {
  if (groupBy === "none") return { All: repos };
  return repos.reduce<Record<string, RepoRecord[]>>((acc, repo) => {
    let key = "Unknown";
    switch (groupBy) {
      case "source":
        key = repo.source_name;
        break;
      case "visibility":
        key = repo.visibility;
        break;
      case "language":
        key = repo.primary_language ?? "No language";
        break;
      case "role":
        key = repo.is_owner ? "Owner" : repo.viewer_role ?? "Unknown";
        break;
      case "fork":
        key = repo.is_fork ? "Fork" : "Original";
        break;
      case "archived":
        key = repo.is_archived ? "Archived" : "Active";
        break;
      default:
        key = "All";
    }
    acc[key] = acc[key] ?? [];
    acc[key].push(repo);
    return acc;
  }, {});
}

export default function App() {
  const [snapshot, setSnapshot] = useState<InventorySnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [views, setViews] = useState<SavedView[]>(() => loadViews());
  const [activeViewId, setActiveViewId] = useState(DEFAULT_VIEWS[0].id);
  const [draftView, setDraftView] = useState<SavedView>(DEFAULT_VIEWS[0]);

  useEffect(() => {
    loadInventory()
      .then(setSnapshot)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load inventory"));
  }, []);

  const filtered = useMemo(
    () => (snapshot ? applyFilters(snapshot.repositories, draftView) : []),
    [snapshot, draftView],
  );

  const grouped = useMemo(() => groupRepos(filtered, draftView.groupBy), [filtered, draftView.groupBy]);

  const languageChart = useMemo(() => {
    const counts = filtered.reduce<Record<string, number>>((acc, repo) => {
      const key = repo.primary_language ?? "Unknown";
      acc[key] = (acc[key] ?? 0) + 1;
      return acc;
    }, {});
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [filtered]);

  const stalenessChart = useMemo(() => {
    const buckets = [
      { name: "0-20", min: 0, max: 20, count: 0 },
      { name: "21-40", min: 21, max: 40, count: 0 },
      { name: "41-60", min: 41, max: 60, count: 0 },
      { name: "61-80", min: 61, max: 80, count: 0 },
      { name: "81-100", min: 81, max: 100, count: 0 },
    ];
    for (const repo of filtered) {
      const bucket = buckets.find((item) => repo.staleness_score >= item.min && repo.staleness_score <= item.max);
      if (bucket) bucket.count += 1;
    }
    return buckets.map(({ name, count }) => ({ name, count }));
  }, [filtered]);

  const sourceOptions = useMemo(() => {
    if (!snapshot) return [];
    return Array.from(new Set(snapshot.repositories.map((repo) => repo.source_name))).sort();
  }, [snapshot]);

  function selectView(id: string) {
    const view = views.find((item) => item.id === id);
    if (!view) return;
    setActiveViewId(id);
    setDraftView(view);
  }

  function updateDraft(patch: Partial<SavedView>) {
    setDraftView((current) => ({ ...current, ...patch }));
  }

  function persistView() {
    const next = views.some((view) => view.id === draftView.id)
      ? views.map((view) => (view.id === draftView.id ? draftView : view))
      : [...views, draftView];
    setViews(next);
    saveViews(next);
    setActiveViewId(draftView.id);
  }

  function applyCardFilter(cardId: SummaryCardId) {
    if (activeCardForView(draftView) === cardId && cardId !== "all") {
      cardId = "all";
    }
    const next = viewForCard(cardId);
    setDraftView(next);
    const matchingPreset = DEFAULT_VIEWS.find((view) => view.id === cardId);
    setActiveViewId(matchingPreset ? matchingPreset.id : cardId === "all" ? "all" : `card-${cardId}`);
  }

  function exportJson() {
    if (!snapshot) return;
    const payload = { ...snapshot, repositories: filtered };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "inventory-filtered.json";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function exportCsv() {
    const header = [
      "full_name",
      "visibility",
      "source_name",
      "is_archived",
      "is_fork",
      "open_pull_request_count",
      "staleness_score",
      "primary_language",
      "pushed_at",
    ];
    const rows = filtered.map((repo) =>
      [
        repo.full_name,
        repo.visibility,
        repo.source_name,
        repo.is_archived,
        repo.is_fork,
        repo.open_pull_request_count,
        repo.staleness_score,
        repo.primary_language ?? "",
        repo.pushed_at ?? "",
      ].join(","),
    );
    const blob = new Blob([[header.join(","), ...rows].join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "inventory-filtered.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  if (error) {
    return (
      <div className="page">
        <div className="error-panel">
          <h1>GitHub Repo Inventory</h1>
          <p>{error}</p>
          <p className="muted">Run <code>uv run github-repo-inventory sync</code> to generate data/inventory.json.</p>
        </div>
      </div>
    );
  }

  if (!snapshot) {
    return <div className="page loading">Loading inventory…</div>;
  }

  return (
    <div className="page">
      <header className="hero">
        <div>
          <p className="eyebrow">GitHub Repository Inventory</p>
          <h1>Repository Dashboard</h1>
          <p className="muted">
            Run {snapshot.summary.run_id} · synced {new Date(snapshot.summary.completed_at).toLocaleString()} · user{" "}
            {snapshot.summary.authenticated_user}
          </p>
        </div>
        <div className="hero-actions">
          <button type="button" onClick={exportCsv}>Export CSV</button>
          <button type="button" onClick={exportJson}>Export JSON</button>
        </div>
      </header>

      <SummaryCards
        repos={filtered}
        allRepos={snapshot.repositories}
        summary={snapshot.summary}
        draftView={draftView}
        onCardClick={applyCardFilter}
      />

      <section className="charts-grid">
        <article className="panel chart-panel">
          <h2>Languages</h2>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={languageChart} dataKey="value" nameKey="name" innerRadius={55} outerRadius={95}>
                {languageChart.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </article>
        <article className="panel chart-panel">
          <h2>Staleness Distribution</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stalenessChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis allowDecimals={false} stroke="#94a3b8" />
              <Tooltip />
              <Bar dataKey="count" fill="#2563eb" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </article>
      </section>

      <FilterBar
        draftView={draftView}
        views={views}
        activeViewId={activeViewId}
        sourceOptions={sourceOptions}
        onSelectView={selectView}
        onChange={updateDraft}
        onSaveView={persistView}
      />

      {Object.entries(grouped).map(([groupName, repos]) => (
        <section key={groupName} className="panel table-panel">
          <div className="panel-header">
            <h2>{draftView.groupBy === "none" ? "Repositories" : groupName}</h2>
            <span className="badge">{repos.length}</span>
          </div>
          <RepoTable repositories={repos} />
        </section>
      ))}
    </div>
  );
}
