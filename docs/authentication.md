# Authentication

This project uses a **fine-grained Personal Access Token (PAT)** to read repository and organization metadata. Classic PATs are not used in this workflow.

## Terminology

| Name | What it is |
|------|------------|
| `GITHUB_TOKEN` | Environment variable **name** in this project (see `config.yaml` → `token_env`) |
| Fine-grained PAT | Token you create at [GitHub fine-grained tokens](https://github.com/settings/personal-access-tokens) — starts with `github_pat_...` |
| Workflow `GITHUB_TOKEN` | Auto-generated Actions token — **not** a PAT; fallback only, too limited for org-wide inventory |

Put your fine-grained PAT in the env var named `GITHUB_TOKEN` locally, or in the `INVENTORY_GITHUB_TOKEN` repository secret for GitHub Actions.

## Required permissions (fine-grained)

When creating the token, set each permission to **Read-only** in the GitHub UI.

### Resource owner (important)

| Resource owner | What you see in the UI | When to use |
|----------------|------------------------|-------------|
| **Your user account** | **Repositories** + **Account** tabs | Default — inventory your repos and org repos you can access |
| **An organization** | **Repositories** + **Organization** tabs | Org-owned token; **Members** appears here, not under Account |

**Members does not exist on the Account tab.** That is expected. Account permissions are for your user profile (email, keys, etc.), not org membership.

For most setups, keep **Resource owner = your user** and configure **Repository permissions** only.

### Repository permissions (Repositories tab)

| GitHub UI label | Access | Used for |
|-----------------|--------|----------|
| **Metadata** | Read-only | Required — repo name, visibility, dates, listing |
| **Pull requests** | Read-only | Open PRs, Dependabot detection |
| **Administration** | Read-only | Merge settings, auto-delete head branches, collaborators |
| **Actions** | Read-only | Whether GitHub Actions is enabled |

**Contents** is not required — this tool does not read repository files.

### Organization permissions (only if Resource owner = organization)

If you set **Resource owner** to an organization (e.g. `cloudsteak`), a separate **Organization** section appears:

| GitHub UI label | Access | Used for |
|-----------------|--------|----------|
| **Members** | Read-only | Org membership context |
| **Administration** | Read-only | Broader org repo listing (org-owned tokens) |

If **Resource owner = your user**, you do **not** need Organization permissions — leave the **Account** tab empty.

### Repository access

- **All repositories** — recommended when Resource owner is your user; includes org repos you can access
- **Only select repositories** — pick specific repos/orgs

```text
Typical setup (Resource owner = your user)

  Repositories tab                 Account tab
  ─────────────────               ───────────
  Metadata          → Read        (leave empty)
  Pull requests     → Read
  Administration    → Read
  Actions           → Read

  Repository access: All repositories
```

Some records may be marked `partial` if the token cannot read certain security or collaborator endpoints. Increase **Administration** to Read-only first; org admins see more fields.

## Create a fine-grained PAT

1. Open [GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens](https://github.com/settings/personal-access-tokens).
2. Click **Generate new token**.
3. **Token name**: `github-repo-inventory`
4. **Expiration**: max **366 days** for org access — the `cloudsteak` org (and many others) reject tokens with longer lifetimes. Use **90 days**, **1 year (365 days)**, or custom ≤ 366 days.
5. **Resource owner**: your user account (or an org if org-owned tokens are enabled for you).
6. **Repository access**: **All repositories** (or select the repos/orgs to inventory).
7. **Permissions**: enable the repository permissions from the table above (all **Read-only**).
8. Click **Generate token**.
9. Copy the token immediately (`github_pat_...`). GitHub shows it only once.

## Local setup

### 1. Config files

```bash
cp config.yaml.example config.yaml
cp .env.example .env
```

Edit `config.yaml`:

```yaml
github:
  token_env: GITHUB_TOKEN
  user: your-github-username
  organizations:
    - your-org
```

### 2. Store the PAT in `.env`

```bash
# .env — never commit this file
GITHUB_TOKEN=github_pat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Run sync

```bash
export $(grep -v '^#' .env | xargs)
uv run github-repo-inventory sync
```

### Verify the token

```bash
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user
```

Expected: JSON with your GitHub user. `401 Bad credentials` means wrong or expired token.

## GitHub Actions setup

The workflow reads:

```yaml
GITHUB_TOKEN: ${{ secrets.INVENTORY_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
```

| Secret | Value | Notes |
|--------|-------|-------|
| **`INVENTORY_GITHUB_TOKEN`** | Fine-grained PAT | **Required for org-wide inventory** |
| **`DASHBOARD_PASSWORD`** | Strong password you choose | Encrypts inventory for GitHub Pages; not stored in git |
| (built-in) `GITHUB_TOKEN` | Workflow token | Fallback only; usually cannot read private org repos |

Secrets are **not** copied when you fork or move the repo — re-create them in the new repository.

### Add the fine-grained PAT as a secret

1. Repository → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**
3. Name: `INVENTORY_GITHUB_TOKEN`
4. Value: your `github_pat_...` token
5. Save

Use the same permission checklist as for local development.

### GitHub Pages (new repository)

1. Make the repository **public** (required on the free plan for Pages).
2. **Settings** → **Pages** → **Build and deployment** → **Source: GitHub Actions**
3. Add the **`DASHBOARD_PASSWORD`** repository secret (same password you use to sign in on the site).
4. Run the workflow — the **`pages-check`** job verifies Pages is enabled before deploy.

If Pages is not enabled, deploy is skipped with a notice; sync and artifacts still run.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Missing GitHub token` | Env var not set | Add PAT to `.env` and export it |
| `401 Bad credentials` | Invalid or expired PAT | Create a new fine-grained token |
| `403` on org repos, message mentions **366 days** | PAT expiration exceeds org policy | Edit token expiration to **≤ 366 days** (e.g. 365 days / 1 year) at [fine-grained tokens](https://github.com/settings/personal-access-tokens) |
| `403` on org repos (other) | Token not approved by org owner, or repo access too narrow | Set **All repositories**; org owner may need to approve the PAT under org Settings → Personal access tokens |
| Empty security / collaborator fields | Insufficient read access | Ensure **Administration** (Read-only) is enabled |
| `partial: true` on records | Some API calls failed | Check `fetch_errors` in JSON output |
| Action only inventories this repo | No `INVENTORY_GITHUB_TOKEN` | Add secret with fine-grained PAT |

## Security hygiene

- Use **Read-only** permissions only.
- Scope repository access to the orgs/repos you actually inventory.
- Set expiration and rotate before expiry.
- Never commit `.env` or paste tokens into `config.yaml`.

## Legacy: Classic PAT (not supported in docs)

This project standardizes on **fine-grained PATs**. Classic tokens (`ghp_...`) may still work but are intentionally undocumented here. Migrate to fine-grained for least-privilege access.
