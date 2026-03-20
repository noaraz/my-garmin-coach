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

Before creating the PR, ask the user:

> "Should this PR include `[Render Preview]` in the title to trigger a Render preview deployment?"

- If **yes**: append ` [Render Preview]` to the PR title and add a placeholder `## Preview` section to the body (the real URL comes after Render deploys — see below)
- If **no**: create the PR without the tag or preview section

### Fetch Render Preview URL (if Render Preview was chosen)

After the PR is created and pushed, Render auto-deploys a preview environment. Poll for the preview URL:

```bash
# Get the latest deployment ID for this PR
DEPLOY_ID=$(gh api repos/noaraz/my-garmin-coach/deployments -q '.[0].id')

# Fetch the environment_url from the deployment status (may take 1-2 minutes after push)
PREVIEW_URL=$(gh api "repos/noaraz/my-garmin-coach/deployments/${DEPLOY_ID}/statuses" -q '.[0].environment_url')
```

If `PREVIEW_URL` is non-empty, update the PR body to include it:

```bash
# Edit the PR body to replace the placeholder with the real preview URL
gh pr edit <PR_NUMBER> --body "...## Preview\n🔗 **[Render Preview](${PREVIEW_URL})**\n..."
```

The preview URL follows the pattern `https://<service-name>-pr-<number>.onrender.com`.
If the deployment isn't ready yet, tell the user and move on — the URL will appear in the GitHub deployment status automatically.

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
