import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { Fragment, useMemo, useState } from "react";
import { RepoRecord } from "../types";

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString();
}

function boolBadge(value: boolean, yes = "Yes", no = "No") {
  return <span className={value ? "pill pill-yes" : "pill pill-no"}>{value ? yes : no}</span>;
}

export function RepoTable({ repositories }: { repositories: RepoRecord[] }) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "staleness_score", desc: true }]);
  const [expanded, setExpanded] = useState<string | null>(null);

  const columns = useMemo<ColumnDef<RepoRecord>[]>(
    () => [
      {
        accessorKey: "full_name",
        header: "Repository",
        cell: ({ row }) => (
          <a href={row.original.html_url} target="_blank" rel="noreferrer" className="repo-link">
            {row.original.full_name}
          </a>
        ),
      },
      { accessorKey: "visibility", header: "Visibility" },
      { accessorKey: "source_name", header: "Source" },
      {
        id: "role",
        header: "Role",
        accessorFn: (row) => (row.is_owner ? "OWNER" : row.viewer_role ?? "—"),
      },
      {
        accessorKey: "open_pull_request_count",
        header: "Open PRs",
      },
      {
        accessorKey: "open_issue_count",
        header: "Open Issues",
      },
      {
        accessorKey: "branch_count",
        header: "Branches",
      },
      {
        id: "branch_protection",
        header: "Protected",
        accessorFn: (row) => row.branch_protection.enabled,
        cell: ({ getValue }) => boolBadge(Boolean(getValue())),
      },
      {
        accessorKey: "primary_language",
        header: "Language",
        cell: ({ getValue }) => getValue<string | null>() ?? "—",
      },
      {
        accessorKey: "pushed_at",
        header: "Last Push",
        cell: ({ getValue }) => formatDate(getValue<string | null>()),
      },
      {
        accessorKey: "staleness_score",
        header: "Staleness",
        cell: ({ getValue }) => {
          const value = getValue<number>();
          const tone = value >= 70 ? "danger" : value >= 40 ? "warn" : "ok";
          return <span className={`score score-${tone}`}>{value.toFixed(0)}</span>;
        },
      },
      {
        id: "details",
        header: "",
        cell: ({ row }) => (
          <button type="button" className="ghost" onClick={() => setExpanded(expanded === row.id ? null : row.id)}>
            Details
          </button>
        ),
      },
    ],
    [expanded],
  );

  const table = useReactTable({
    data: repositories,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getRowId: (row) => row.full_name,
  });

  return (
    <div className="table-wrap">
      <table>
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id} onClick={header.column.getToggleSortingHandler()}>
                  {flexRender(header.column.columnDef.header, header.getContext())}
                  {{ asc: " ↑", desc: " ↓" }[header.column.getIsSorted() as string] ?? null}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <Fragment key={row.id}>
              <tr>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                ))}
              </tr>
              {expanded === row.id ? (
                <tr key={`${row.id}-details`} className="details-row">
                  <td colSpan={columns.length}>
                    <RepoDetails repo={row.original} />
                  </td>
                </tr>
              ) : null}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RepoDetails({ repo }: { repo: RepoRecord }) {
  return (
    <div className="details-grid">
      <div>
        <h3>Lifecycle</h3>
        <ul>
          <li>Created: {formatDate(repo.created_at)}</li>
          <li>Updated: {formatDate(repo.updated_at)}</li>
          <li>Archived: {repo.is_archived ? "Yes" : "No"}</li>
          <li>Template: {repo.is_template ? "Yes" : "No"}</li>
          <li>Inactive: {repo.is_inactive ? "Yes" : "No"} ({repo.days_since_last_push ?? "—"} days)</li>
        </ul>
      </div>
      <div>
        <h3>Fork</h3>
        <ul>
          <li>Is fork: {repo.is_fork ? "Yes" : "No"}</li>
          <li>Source: {repo.fork_source ?? "—"}</li>
          <li>Forks: {repo.forks_count}</li>
        </ul>
      </div>
      <div>
        <h3>Merge Settings</h3>
        <ul>
          <li>Auto-delete head branches: {repo.merge_settings.delete_branch_on_merge ? "Enabled" : "Disabled"}</li>
          <li>Merge commit: {repo.merge_settings.allow_merge_commit ? "Allowed" : "Blocked"}</li>
          <li>Squash: {repo.merge_settings.allow_squash_merge ? "Allowed" : "Blocked"}</li>
          <li>Rebase: {repo.merge_settings.allow_rebase_merge ? "Allowed" : "Blocked"}</li>
          <li>Default method: {repo.merge_settings.default_merge_method ?? "—"}</li>
        </ul>
      </div>
      <div>
        <h3>Security</h3>
        <ul>
          <li>Dependabot alerts: {formatNullableBool(repo.security.dependabot_alerts_enabled)}</li>
          <li>Dependabot updates: {formatNullableBool(repo.security.dependabot_security_updates_enabled)}</li>
          <li>Secret scanning: {formatNullableBool(repo.security.secret_scanning_enabled)}</li>
          <li>Code scanning: {formatNullableBool(repo.security.code_scanning_enabled)}</li>
          <li>Actions enabled: {formatNullableBool(repo.actions_enabled)}</li>
        </ul>
      </div>
      <div className="wide">
        <h3>Open Pull Requests</h3>
        {repo.open_pull_requests.length ? (
          <ul>
            {repo.open_pull_requests.map((pr) => (
              <li key={pr.number}>
                <a href={pr.url} target="_blank" rel="noreferrer">#{pr.number} {pr.title}</a>
                {" · "}
                {pr.author_login}
                {pr.is_dependabot ? " · dependabot" : ""}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No open pull requests.</p>
        )}
      </div>
      <div className="wide">
        <h3>Topics & License</h3>
        <p>{repo.topics.length ? repo.topics.join(", ") : "No topics"}</p>
        <p>License: {repo.license_name ?? repo.license_spdx ?? "—"}</p>
        <p>Size: {repo.size_kb} KB · Default branch: {repo.default_branch ?? "—"}</p>
      </div>
      {(repo.collaborators.length > 0 || repo.teams.length > 0) && (
        <div className="wide">
          <h3>Access</h3>
          {repo.collaborators.length > 0 && <p>Collaborators: {repo.collaborators.map((c) => `${c.login} (${c.permission})`).join(", ")}</p>}
          {repo.teams.length > 0 && <p>Teams: {repo.teams.map((t) => `${t.name} (${t.permission})`).join(", ")}</p>}
        </div>
      )}
      {repo.partial && (
        <div className="wide warning">
          Partial sync: {repo.fetch_errors.join("; ")}
        </div>
      )}
    </div>
  );
}

function formatNullableBool(value: boolean | null): string {
  if (value === null) return "Unknown";
  return value ? "Yes" : "No";
}
