# GitHub Repo Inventory

Discover, inventory, and visualize GitHub repositories across your user account and organizations.

## Features

- **Repository discovery** for a configured user, optional additional users, and organizations
- **Rich metadata collection** including pull requests, branch protection, merge settings, security features, collaborators, and teams
- **Staleness scoring** to highlight inactive or risky repositories
- **SQLite history** with timestamped JSON run snapshots and diff support
- **Interactive dashboard** with filters, saved views, grouping, charts, and export
- **GitHub Actions workflow** for scheduled sync and optional GitHub Pages deployment

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Node.js 22+ for the dashboard
- GitHub **fine-grained PAT** — see [Authentication guide](docs/authentication.md)

## Quick start

### 1. Install Python dependencies

```bash
uv sync
```

### 2. Configure access

See the full guide: **[Authentication — fine-grained PAT](docs/authentication.md)**

```bash
cp config.yaml.example config.yaml
cp .env.example .env
```

Edit `config.yaml`:

```yaml
github:
  token_env: GITHUB_TOKEN   # env var name — not the token itself
  user: your-github-username
  organizations:
    - your-org
  include_forks: true
  include_archived: true
```

Create a **fine-grained PAT**: [github.com/settings/personal-access-tokens](https://github.com/settings/personal-access-tokens)

Put it in `.env`:

```bash
# .env — do not commit
GITHUB_TOKEN=github_pat_xxxxxxxxxxxx
```

**Required permissions on the Repositories tab (all Read-only):** Metadata, Pull requests, Administration, Actions

**Account tab:** leave empty (Members is not there — that is normal)

**Repository access:** All repositories

Details: [docs/authentication.md](docs/authentication.md#resource-owner-important)

### 3. Run sync

The CLI loads `.env` automatically from the project root:

```bash
uv run github-repo-inventory sync
```

Or export manually:

```bash
export $(grep -v '^#' .env | xargs)
uv run github-repo-inventory sync
```

Outputs:

- `data/inventory.db`
- `data/inventory.json`
- `data/runs/inventory-<timestamp>.json`

### 4. Launch dashboard

After `sync`, inventory files are copied automatically to `dashboard/public/` (disable with `storage.auto_publish_dashboard: false` in config).

```bash
cd dashboard
npm install
npm run dev
```

Dev mode reads `data/inventory.json` directly; `dashboard/public/` is used for `npm run preview` and `npm run build`.

Open the local Vite URL shown in the terminal.

## CLI commands

```bash
uv run github-repo-inventory sync
uv run github-repo-inventory list-runs
uv run github-repo-inventory export
uv run github-repo-inventory export --csv data/inventory.csv
uv run github-repo-inventory diff RUN_A RUN_B
uv run github-repo-inventory diff-files data/runs/inventory-OLD.json
```

## GitHub Actions

Workflow file: [`.github/workflows/inventory.yml`](.github/workflows/inventory.yml)

Behavior:

- Runs weekly on Monday at 06:00 UTC
- Supports manual `workflow_dispatch`
- Commits updated inventory snapshots to the repository
- Builds and deploys the dashboard to GitHub Pages

### Action setup

Full setup: [docs/authentication.md](docs/authentication.md#github-actions-setup)

1. Enable GitHub Pages manually (required once): **Settings** → **Pages** → **Build and deployment** → **Source: GitHub Actions**. The workflow token cannot create a Pages site automatically.
2. Create a **fine-grained PAT** with the [permission checklist](docs/authentication.md#required-permissions-fine-grained).
3. Add it as repository secret **`INVENTORY_GITHUB_TOKEN`** (`Settings` → `Secrets and variables` → `Actions`).
4. Update the generated `config.yaml` step in the workflow with your org list, or commit a safe `config.yaml` template and inject orgs via workflow inputs.

If `INVENTORY_GITHUB_TOKEN` is not set, the workflow falls back to the built-in `GITHUB_TOKEN`, which is **not** a PAT and is usually limited to the current repository.

## Project layout

```text
.
├── config.yaml.example
├── data/
├── dashboard/
├── docs/
│   ├── authentication.md
│   ├── architecture.md
│   └── fields.md
├── src/github_repo_inventory/
└── tests/
```

## Documentation

- [Authentication — fine-grained PAT](docs/authentication.md)
- [Architecture](docs/architecture.md)
- [Collected fields](docs/fields.md)

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests
```

## License

MIT
