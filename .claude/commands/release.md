# /release — Release Workflow

Run this workflow when you're ready to cut a production release. Follow the steps in order.

---

## 1. Pre-flight Checks

Verify the repo is in a clean, releasable state:

```bash
# Must be on main and up to date
git checkout main && git pull

# Must be clean (no uncommitted changes)
git status

# Show recent commits since last tag (what's in this release)
git log $(git describe --tags --abbrev=0 2>/dev/null || echo "")..HEAD --oneline
```

Present the commit list to the user. If there are uncommitted changes, stop and ask the user to commit or stash them first.

Then verify the Neon production DB is at a known alembic revision (catches stale stamps before deploy):

```bash
# Load DATABASE_URL from .env.prod and check alembic state
# Must output: <revision-id> (head)
source .env.prod && DATABASE_URL=$DATABASE_URL backend/.venv/bin/alembic -c backend/alembic.ini current
```

If this fails with "Can't locate revision", follow the fix in CLAUDE.md → "When alembic_version has an unknown revision". **Do not tag until this is resolved.**

---

## 2. Run Full Test Suite

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose exec backend pytest tests/ -v --cov=src --cov-report=term-missing
```

Also run frontend tests:

```bash
cd frontend && npm run test:run && npm run build
```

Present results. If any tests fail, stop and ask the user what to do.

---

## 3. Security Review

Run the code review with a security focus:

```
/code-review uncommitted changes
```

Present any issues with confidence score ≥ 80. Ask the user:

> "Security review complete. Any findings to fix before tagging?"

Wait for their response. Fix any flagged items, re-run tests, then continue.

---

## 4. Determine Version

Get the current latest tag:
```bash
git describe --tags --abbrev=0
```

Use the `AskUserQuestion` tool with a single question and three options. Compute the next PATCH/MINOR/MAJOR versions from the current tag and include them in the option labels. Example structure (replace vX.Y.Z with actual computed values):

```
Question: "What version should this release be? (current latest tag: vX.Y.Z)"
Header: "Version"
Options:
  - label: "vX.Y.Z+1 — PATCH"  description: "Bug fixes, no schema change"
  - label: "vX.Y+1.0 — MINOR"  description: "New features, may include a migration"
  - label: "vX+1.0.0 — MAJOR"  description: "Breaking API or schema changes"
```

Wait for their selection.

---

## 5. Bump `frontend/package.json`, Update STATUS.md, and Open a PR

**main is protected — never push directly. Always use a PR.**

Create a release branch, bump the version, update STATUS.md, and open a PR:

```bash
git checkout main && git pull
git checkout -b release/<VERSION>

# Check current value
node -e "const p = require('./frontend/package.json'); console.log('current:', p.version)"
```

Update `frontend/package.json` version to match the release tag (strip the leading `v`).

Also update `STATUS.md` — add a release entry at the top and update `Last updated:`. Both changes must be in the **same commit**.

```
# STATUS.md changes:
# - Update "Last updated:" line to today's date
# - Add a ## vX.Y.Z Release ✅ section at the top with the release tasks table
```

Then commit, push the branch, and open a PR:

```bash
git add frontend/package.json STATUS.md
git commit -m "chore: bump version to <VERSION>"
git push -u origin release/<VERSION>
gh pr create --title "chore: bump version to <VERSION>" --base main --head release/<VERSION> --body "..."
```

This commit is what gets tagged. The sidebar reads `package.json` at build time and STATUS.md reflects the release immediately — tagging alone does **not** update either.

---

## 6. Pre-Release Checklist

Run these checks on the **release branch** (before the PR is merged) to catch issues early.

```bash
# 1. Verify frontend/package.json version matches the release tag
node -e "const p = require('./frontend/package.json'); console.log(p.version)"

# 2. Verify no uncommitted changes remain on the release branch
git status

# 3. Check for any secrets accidentally staged (gitleaks-style quick check)
git log --oneline -5

# 4. Check if any Alembic migration files were added in commits since last tag
git diff $(git describe --tags --abbrev=0)..HEAD --name-only | grep alembic/versions || echo "No migrations in this release"

# 5. Verify RENDER_DEPLOY_HOOK_URL is set in GitHub Actions secrets
gh secret list | grep RENDER_DEPLOY_HOOK_URL || echo "WARNING: RENDER_DEPLOY_HOOK_URL not found"
```

Present verified results, then ask the user to confirm any items you could not auto-verify:

> Pre-release checks:
> - [auto] `frontend/package.json` version: `<verified value>`
> - [auto] Working tree: clean / <issues found>
> - [auto] Alembic migrations in this release: yes/no
> - [auto] `RENDER_DEPLOY_HOOK_URL` secret: present / NOT FOUND
> - [ ] All features for this release are merged to `main` — please confirm

---

## 7. Monitor PR CI and Notify

After opening the release PR, poll CI until it completes. Do not proceed to merge or ask release notes questions until CI is confirmed green.

```bash
# Get the run ID for the release branch CI
gh run list --repo noaraz/my-garmin-coach --branch release/<VERSION> --limit 3

# Watch until complete (exits when done)
gh run watch <run-id>
```

When CI completes:
- **Pass**: notify the user: "CI passed on PR #<N>. Ready to merge." Then present the full pre-release summary and wait for the user to confirm all items before asking them to merge.
- **Fail**: show the failure summary (`gh run view <run-id> --log-failed`) and stop. Do not proceed until the user decides how to fix it.

After the user confirms and merges the PR, pull main:
```bash
git checkout main && git pull
```

---

## 8. Release Notes

Ask the user:

> Write a short summary (1 line) and bullet-point release notes for this release.
> These will appear on the GitHub Release page.
>
> Example:
> ```
> Summary: First production release
>
> - HTTP security headers on API and frontend
> - HKDF key derivation for Garmin token encryption
> - Password manager support on login and register forms
> - Automated release pipeline with approval gate
> ```

Wait for their notes.

---

## 9. Tag and Push

```bash
# Ensure on main and up to date (PR must be merged first)
git checkout main && git pull

# Create annotated tag — summary on first -m, notes on second -m
git tag -a <VERSION> -m "<one-line summary>" -m "<bullet notes>"

# Push the tag (main is already on remote via the merged PR)
git push origin <VERSION>
```

After pushing, print:

> Tag `<VERSION>` pushed. GitHub Actions will now:
> 1. Run the full test suite
> 2. Run security checks (bandit, pip-audit, npm audit, gitleaks)
> 3. Create the GitHub Release automatically if all checks pass
>
> Monitor progress: `gh run list --limit 3`
> Or view on GitHub: Actions tab → Release workflow

---

## 10. Monitor the Release Pipeline

The tag push from step 6 triggers the Release workflow. The pipeline pauses for your approval after tests:

```
security-and-tests → [APPROVAL GATE] → create-release → deploy to Render
```

**What happens:**
1. Tests + security checks run automatically (~3 min)
2. GitHub pauses and sends you an email: *"Your workflow is waiting for approval"*
3. **You review** → go to **GitHub → Actions → Release workflow → Review deployments** → Approve or Reject
4. If approved: GitHub Release is created, then Render deploy fires
5. If rejected: pipeline stops — no release, no deploy

Monitor:
```bash
gh run list --limit 3
```

Watch the Render build: **Render Dashboard → garmincoach → Logs**

---

**One-time setup** (only needed once):
> GitHub repo → **Settings → Environments → New environment** → name it `production`
> → **Required reviewers** → add yourself → Save

If the deploy hook isn't set up yet:
> Set `RENDER_DEPLOY_HOOK_URL` in GitHub → Settings → Secrets → Actions.
> Get the URL from: Render Dashboard → garmincoach → Settings → Deploy Hook.

---

## 11. Post-Deploy Verification

After Render shows the deploy as live:

> - [ ] Visit `https://garmincoach.onrender.com` — app loads
> - [ ] Sidebar shows `v<VERSION>` (not `-dev` suffix, not a stale version number)
> - [ ] Login works
> - [ ] If first deploy: create admin user via Render Shell (see below)
> - [ ] If Garmin was connected: reconnect in Settings (HKDF change invalidated old tokens)

**First deploy only** — create admin user in Render Shell:
```python
python3 - <<'EOF'
import asyncio, os
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from src.db.models import AthleteProfile
from src.auth.models import User
from src.auth.utils import get_password_hash

async def main():
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with AsyncSession(engine) as session:
        user = User(email="your@email.com", hashed_password=get_password_hash("yourpassword"))
        session.add(user)
        await session.commit()
        print(f"Created: {user.email}")

asyncio.run(main())
EOF
```
