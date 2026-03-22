# /ship — Feature Ship Workflow

Run this workflow when a feature is ready to ship. Follow the steps in order.

---

## 1. Run Tests

Run the full test suite with coverage inside Docker:

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose exec backend pytest tests/ -v --cov=src --cov-report=term-missing
```

Present results to the user: total passed/failed, coverage per module, any failures.

---

## 2. Lint

Run linters before opening the PR — these mirror CI exactly:

```bash
# Backend: ruff lint (catches unused imports, style violations)
cd backend && ruff check src/ tests/

# Frontend: TypeScript type check + build
cd frontend && npm run build
```

Fix any errors before continuing. For ruff: `ruff check --fix src/ tests/` auto-fixes safe issues.

---

## 3. Security Audit

Run security checks before opening the PR:

```bash
# Frontend: fail on high-severity CVEs
cd frontend && npm audit --audit-level=high

# Backend: fail on known vulnerabilities
pip-audit --ignore-vuln GHSA-25h7-pfq9-p65f  # ecdsa, no fix available
```

If `npm audit` flags new high/critical CVEs: run `npm audit fix` (or `npm audit fix --force` if needed), commit `package-lock.json`, then continue.

---

## 4. Ask What to Fix (Pre-PR)

Show the test results and ask:

> "Tests look good. Anything to fix before I open the PR?"

Wait for the user's response. Fix any requested items, re-run the affected tests to confirm green, then continue.

---

## 5. Local Test Steps

Print this block for the user to run manually:

```bash
# Unit tests
/Applications/Docker.app/Contents/Resources/bin/docker compose exec backend pytest tests/unit/ -v

# Integration tests
/Applications/Docker.app/Contents/Resources/bin/docker compose exec backend pytest tests/integration/ -v

# Full suite + coverage
/Applications/Docker.app/Contents/Resources/bin/docker compose exec backend pytest tests/ --cov=src --cov-report=term-missing

# Smoke test the API
curl http://localhost:8000/api/v1/health
```

---

## 6. Update All Relevant Docs

### STATUS.md
- Mark all completed tasks as ✅
- Update "Last updated" line with today's date and feature name
- Update `## Current Focus` to the next feature

### CLAUDE.md
- Add any new patterns, gotchas, or conventions discovered
- Update the Features table if new implementation files were added

### `features/<name>/PLAN.md`
- Check off all completed tasks
- Note any deviations from the original plan

### `features/<name>/CLAUDE.md`
- Add gotchas, edge cases, or patterns specific to this feature
- Update mock/fixture patterns if they changed

---

## 7. Commit and Open PR

Stage and review:
```bash
git add -A
git status
```

Commit (conventional style):
```bash
git commit -m "feat: <short description>"
```

### Ask about Render Preview

Before creating the PR, use the `AskUserQuestion` tool to ask:

```
Question: "Should this PR include [Render Preview] in the title to trigger a Render preview deployment?"
Header: "Render Preview"
Options:
  - Yes — append [Render Preview] to the PR title and add a placeholder ## Preview section to the body
  - No  — create the PR without the tag or preview section
```

Wait for the user's answer before creating the PR.

### Fetch Render Preview URL and Check Deployment (if Render Preview was chosen)

After the PR is created and pushed, Render auto-deploys a preview environment via the GitHub Deployments API.

**Step 1 — Get preview URL and deployment state:**

```bash
# Get the latest deployment ID for this PR
DEPLOY_ID=$(gh api repos/noaraz/my-garmin-coach/deployments -q '.[0].id')

# Fetch state, URL, and log link from the deployment status
gh api "repos/noaraz/my-garmin-coach/deployments/${DEPLOY_ID}/statuses" \
  -q '.[0] | {state, environment_url, log_url}'
```

**Step 2 — Interpret the deployment state:**

| State | Meaning | Action |
|-------|---------|--------|
| `success` | Deployed and running | Add preview URL to PR body |
| `in_progress` | Still building | Wait ~2 min, re-check |
| `inactive` | Deployed but spun down (free tier idle) | Add preview URL — it will wake on first request (~30s) |
| `failure` | Build or startup crashed | **Investigate.** Check the `log_url` in the Render dashboard. Common causes: missing env vars, failed alembic migration, import errors. Ask user to share the Render log output so you can diagnose. |
| `error` | Render infra issue | Retry or check Render status page |

**Step 3 — Update PR body with the real preview URL:**

```bash
PREVIEW_URL=$(gh api "repos/noaraz/my-garmin-coach/deployments/${DEPLOY_ID}/statuses" -q '.[0].environment_url')
gh pr edit <PR_NUMBER> --body "...## Preview\n🔗 **[Render Preview](${PREVIEW_URL})**\n..."
```

**Step 4 — If deployment failed:**

Tell the user the deployment failed and provide the Render dashboard log link. Common failures on preview deploys:
- **Missing env vars**: Preview instances don't inherit all env vars from the main service. Check `DATABASE_URL`, `GARMINCOACH_SECRET_KEY`, `GOOGLE_CLIENT_ID` are set in Render's preview env config.
- **Alembic migration failure**: New migration may fail on a fresh DB or with schema drift. Check the `alembic upgrade head` output in the log.
- **Import/syntax error**: A Python import that works locally but breaks in the Docker build (missing dependency, wrong path).

Ask the user to paste the relevant log lines so you can fix the root cause.

### Create the PR

```bash
gh pr create \
  --title "feat: <title>" \
  --body "$(cat <<'EOF'
## Summary
- <bullet 1>
- <bullet 2>
- <bullet 3>

## Test plan
- [ ] Unit tests pass: `pytest tests/unit/ -v`
- [ ] Integration tests pass: `pytest tests/integration/ -v`
- [ ] Coverage ≥ 80%: `pytest tests/ --cov=src --cov-report=term-missing`
- [ ] API smoke test: `curl http://localhost:8000/api/v1/health`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Return the PR URL to the user.

---

## 8. Code Review on the PR

Now that the PR exists, invoke the `code-review:code-review` skill on it:

```
Skill tool: code-review:code-review, args: <PR URL>
```

Present any issues found to the user and offer to fix them.
