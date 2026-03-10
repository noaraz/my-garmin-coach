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

## 4. Pre-Release Checklist

Ask the user to confirm each item:

> Before tagging, please confirm:
> - [ ] All features for this release are merged to `main`
> - [ ] No secrets are in the code or git history
> - [ ] If schema changed: Alembic migration created, tested locally, and ready to apply on Render
> - [ ] Render is up and will auto-deploy when `main` is pushed

---

## 5. Determine Version

Ask the user:

> What version should this release be? (current latest tag: `git describe --tags --abbrev=0`)
>
> Versioning guide (from RELEASING.md):
> - `PATCH` — bug fixes, no schema change
> - `MINOR` — new features, may include a migration
> - `MAJOR` — breaking API or schema changes

Wait for their answer (e.g. `v1.0.0`).

---

## 6. Tag and Push

```bash
# Create annotated tag
git tag -a <VERSION> -m "<one-line release summary>"

# Push the tag — this triggers the GitHub Actions security gate
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

## 7. Update STATUS.md

- Mark `Tag v1.0.0 + create GitHub Release` as ✅
- Update `Last updated` line
- Update `## Current Focus` to the next item

---

## 8. Post-Release (if first deploy)

If this is the first Render deploy, remind the user:

> After the Render deploy completes, run in the Render shell:
> ```bash
> cd /app && python -m alembic stamp head
> ```
> See `RELEASING.md` for the full post-deploy checklist.
