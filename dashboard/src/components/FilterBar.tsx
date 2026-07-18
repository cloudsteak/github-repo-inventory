import { SavedView } from "../types";

interface Props {
  draftView: SavedView;
  views: SavedView[];
  activeViewId: string;
  sourceOptions: string[];
  onSelectView: (id: string) => void;
  onChange: (patch: Partial<SavedView>) => void;
  onSaveView: () => void;
}

export function FilterBar({
  draftView,
  views,
  activeViewId,
  sourceOptions,
  onSelectView,
  onChange,
  onSaveView,
}: Props) {
  return (
    <section className="panel filters">
      <div className="panel-header">
        <h2>Filters & Views</h2>
        <div className="view-tabs">
          {views.map((view) => (
            <button
              key={view.id}
              type="button"
              className={view.id === activeViewId ? "tab active" : "tab"}
              onClick={() => onSelectView(view.id)}
            >
              {view.name}
            </button>
          ))}
        </div>
      </div>

      <div className="filters-grid">
        <label>
          Search
          <input
            value={draftView.search}
            onChange={(event) => onChange({ search: event.target.value })}
            placeholder="Name, language, topic…"
          />
        </label>

        <label>
          Source
          <select value={draftView.source} onChange={(event) => onChange({ source: event.target.value })}>
            <option value="all">All</option>
            {sourceOptions.map((source) => (
              <option key={source} value={source}>{source}</option>
            ))}
          </select>
        </label>

        <label>
          Visibility
          <select value={draftView.visibility} onChange={(event) => onChange({ visibility: event.target.value })}>
            <option value="all">All</option>
            <option value="public">Public</option>
            <option value="private">Private</option>
            <option value="internal">Internal</option>
          </select>
        </label>

        <label>
          Archived
          <select value={draftView.archived} onChange={(event) => onChange({ archived: event.target.value })}>
            <option value="all">All</option>
            <option value="no">Active only</option>
            <option value="yes">Archived only</option>
          </select>
        </label>

        <label>
          Fork
          <select value={draftView.fork} onChange={(event) => onChange({ fork: event.target.value })}>
            <option value="all">All</option>
            <option value="no">Original only</option>
            <option value="yes">Forks only</option>
          </select>
        </label>

        <label>
          Open PRs
          <select value={draftView.hasOpenPr} onChange={(event) => onChange({ hasOpenPr: event.target.value })}>
            <option value="all">All</option>
            <option value="yes">Has open PRs</option>
            <option value="no">No open PRs</option>
          </select>
        </label>

        <label>
          Group by
          <select value={draftView.groupBy} onChange={(event) => onChange({ groupBy: event.target.value })}>
            <option value="none">None</option>
            <option value="source">Source</option>
            <option value="visibility">Visibility</option>
            <option value="language">Language</option>
            <option value="role">Role</option>
            <option value="fork">Fork status</option>
            <option value="archived">Archived status</option>
          </select>
        </label>

        <label className="checkbox">
          <input
            type="checkbox"
            checked={draftView.dependabotOnly}
            onChange={(event) => onChange({ dependabotOnly: event.target.checked })}
          />
          Dependabot PRs only
        </label>

        <label className="checkbox">
          <input
            type="checkbox"
            checked={draftView.inactiveOnly}
            onChange={(event) => onChange({ inactiveOnly: event.target.checked })}
          />
          Inactive only
        </label>
      </div>

      <div className="filters-actions">
        <button type="button" onClick={onSaveView}>Save current view</button>
      </div>
    </section>
  );
}
