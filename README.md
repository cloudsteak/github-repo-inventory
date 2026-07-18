# GitHub Repo Inventory

Discover, inventory, and visualize GitHub repositories across your user account and organizations.

## Features

- **Repository discovery** for a configured user, optional additional users, and organizations
- **Rich metadata collection** including pull requests, branch protection, merge settings, security features, collaborators, and teams
- **Staleness scoring** to highlight inactive or risky repositories
- **SQLite history** with timestamped JSON run snapshots and diff support
- **Interactive dashboard** with filters, saved views, grouping, charts, and export
- **GitHub Actions workflow** for scheduled sync and password-protected GitHub Pages deployment

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

Optional password for local dev/preview — add to `.env`:

```bash
DASHBOARD_PASSWORD=your-secret-password
```

When set locally, the dev server requires sign-in before serving plain `inventory.json`.

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
- Uploads inventory snapshots as workflow artifacts
- Deploys a **password-protected** dashboard to GitHub Pages

### Password-protected GitHub Pages

GitHub Pages serves static files only. The pipeline encrypts inventory at **build time** using the **`DASHBOARD_PASSWORD` repository secret** — the password is never committed to git and never embedded in the JavaScript bundle.

| Location | What is stored |
|----------|----------------|
| GitHub Secret `DASHBOARD_PASSWORD` | The password (you choose it once) |
| Pipeline runtime | Secret injected as env var, used to encrypt, then discarded |
| Published site (`inventory.enc.json`) | Encrypted blob only — useless without the password |
| Source code / public repo | Encryption **logic** only, not the key |

Someone with the full source code but **without** the secret cannot decrypt the data. They only see the same public `inventory.enc.json` as everyone else.

Flow:

1. Add **`DASHBOARD_PASSWORD`** under **Settings** → **Secrets and variables** → **Actions**
2. Each workflow run reads the secret, runs `encrypt-inventory.mjs`, deploys only `inventory.enc.json`
3. Open the Pages URL and enter the same password — the browser decrypts locally

Use a strong, unique password. This protects against casual access; a determined attacker with the encrypted file could still attempt offline cracking of a weak password.

### Data privacy

Inventory data includes repository names, visibility, collaborators, security settings, and open PRs. Treat it as **internal-only** even when encrypted on Pages.

### Action setup

Full setup: [docs/authentication.md](docs/authentication.md#github-actions-setup)

1. Create a **fine-grained PAT** with the [permission checklist](docs/authentication.md#required-permissions-fine-grained).
2. Add it as repository secret **`INVENTORY_GITHUB_TOKEN`** (`Settings` → **Secrets and variables** → **Actions**).
3. Add **`DASHBOARD_PASSWORD`** for encrypted GitHub Pages deployment.
4. Set inventory scope: repository variables **`INVENTORY_USER`** (personal repos) and **`INVENTORY_ORGS`** (comma-separated), or edit the workflow `Create config` step.

If `INVENTORY_GITHUB_TOKEN` is not set, the workflow falls back to the built-in `GITHUB_TOKEN`, which is **not** a PAT and is usually limited to the current repository.

### New repository checklist

When you fork, clone, or move this project to a **new GitHub repository**, GitHub does **not** copy secrets, Pages settings, or environments. Set these up again:

| Step | Where | Required for |
|------|-------|--------------|
| 1. **`INVENTORY_GITHUB_TOKEN`** secret | Settings → Secrets and variables → Actions | Org-wide inventory sync |
| 2. **`DASHBOARD_PASSWORD`** secret | Settings → Secrets and variables → Actions | Encrypted Pages deploy |
| 3. **GitHub Pages** enabled | Settings → Pages → Source: **GitHub Actions** | Dashboard hosting (`pages-check` job) |
| 4. Repository **public** (free plan) | Settings → General → visibility | Free GitHub Pages |
| 5. **`github-pages` environment** | Created automatically on first deploy (or Settings → Environments) | Pages deployment job |
| 6. **Inventory scope** | Repository variables `INVENTORY_USER` (default: `the1bit`) and `INVENTORY_ORGS` (default: `cloudsteak`) — or edit the workflow `Create config` step | Personal user repos + org repos |
| 7. **Fine-grained PAT org approval** | Org Settings → Personal access tokens (if org policy requires it) | PAT access to org repos |
| 8. **First workflow run** | Actions → Inventory Sync → Run workflow | Verify sync + deploy |

Until step 3 is done, the **`pages-check`** job logs a notice and **`deploy-dashboard` is skipped** — sync and artifacts still work.

Dashboard URL after deploy: `https://<owner>.github.io/<repo>/` (sign in with the same password as `DASHBOARD_PASSWORD`).

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
